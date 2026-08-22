# -*- coding: utf-8 -*-
"""Llama 推理服务：读 config.json 模型表，本地启停 llama-server。"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request

from . import config as cfg

_LOCK = threading.RLock()
# 大模型加载可能超过 1 分钟；端口通 ≠ 推理就绪
_READY_TIMEOUT_SEC = 300

# 本机推理必须直连：绕过系统代理环境变量（HTTP_PROXY/HTTPS_PROXY），
# 否则 /health、/v1/models 会走代理失败，误判 llama 未就绪并长时间空等。
_NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get_model_keys() -> list[str]:
    return list(cfg.models_registry().keys())


def get_model_labels() -> list[str]:
    models = cfg.models_registry()
    return [str(m.get("label") or k) for k, m in models.items()]


def key_from_label(label: str) -> str:
    models = cfg.models_registry()
    for k, m in models.items():
        if str(m.get("label") or k) == label:
            return k
    return label


def get_selected_model() -> str:
    return cfg.get_selected_model_key()


def set_model(key: str) -> bool:
    if key not in cfg.models_registry():
        return False
    cfg.set_selected_model_key(key)
    return True


def is_port_open(port: int) -> bool:
    if not port:
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        try:
            return s.connect_ex(("127.0.0.1", port)) == 0
        except Exception:
            return False


def service_status() -> dict[str, bool]:
    ready = is_llama_ready()
    return {"llama": ready, "port": is_port_open(cfg.llama_port()), "ready": ready}


def _http_get_json(path: str, *, timeout: float = 3.0) -> tuple[int | None, object | None]:
    url = f"{cfg.llama_backend_url().rstrip('/')}{path}"
    try:
        req = urllib.request.Request(url, method="GET")
        with _NO_PROXY_OPENER.open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, None
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, None


def is_llama_ready(expected_alias: str | None = None) -> bool:
    """端口通还不够：必须 /health 正常（若有），且（可选）当前模型 alias 匹配。"""
    if not is_port_open(cfg.llama_port()):
        return False
    health_code, _ = _http_get_json("/health", timeout=2.0)
    # /health 存在但未 200 → 仍在加载
    if health_code is not None and health_code != 200:
        return False
    code, data = _http_get_json("/v1/models", timeout=2.0)
    if code != 200 or not isinstance(data, dict):
        return False
    if not expected_alias:
        return True
    items = data.get("data") or []
    if not items:
        return False
    loaded = str(items[0].get("id") or "").strip()
    return loaded == expected_alias


def wait_until_ready(
    *,
    expected_alias: str | None = None,
    timeout_sec: int = _READY_TIMEOUT_SEC,
    label: str = "",
) -> tuple[bool, str]:
    """阻塞等待模型真正可推理，避免工作流提前进入下一节点。"""
    deadline = time.time() + max(30, int(timeout_sec))
    last_note = "等待中"
    while time.time() < deadline:
        if is_llama_ready(expected_alias):
            name = label or expected_alias or "Llama"
            return True, f"模型已就绪: {name}"
        if not is_port_open(cfg.llama_port()):
            last_note = "等待端口打开"
        else:
            last_note = "端口已开，等待模型加载完成"
        time.sleep(1.0)
    return False, f"模型加载超时（{timeout_sec}s）：{last_note}。请检查显存与模型路径。"


def _build_args(model_key: str | None = None) -> list[str]:
    key = model_key or cfg.get_selected_model_key()
    models = cfg.models_registry()
    if key not in models:
        raise ValueError(f"未知模型: {key or '(未配置)'}")
    m = models[key]
    model_path = str(m.get("model") or "")
    if not model_path or not os.path.isfile(model_path):
        raise FileNotFoundError(f"模型文件不存在: {model_path}")

    args = ["-m", model_path]
    mmproj = str(m.get("mmproj") or "").strip()
    if mmproj:
        if not os.path.isfile(mmproj):
            raise FileNotFoundError(f"mmproj 不存在: {mmproj}")
        args += ["--mmproj", mmproj]

    ngl = m.get("ngl", "99")
    args += [
        "--alias", str(m.get("alias") or key),
        "--reasoning", "off",
        "--reasoning-budget", "0",
        "--jinja",
    ]
    if ngl is not None and str(ngl).lower() not in ("auto", ""):
        args += ["-ngl", str(ngl)]

    port = cfg.llama_port()
    args += [
        "--split-mode", "none",
        "-np", "1",
        "-c", str(m.get("ctx", "8192")),
        "--flash-attn", "on",
        "--cache-type-k", "q4_0",
        "--cache-type-v", "q4_0",
        "-b", "512",
        "-ub", "512",
        "--threads", cfg.llama_threads(),
        "--threads-batch", cfg.llama_threads(),
        "--poll", "50",
        "--prio", "2",
        "--temp", "0.2",
        "--top-p", "0.9",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--no-mmap",
    ]
    if mmproj:
        args += ["--image-min-tokens", "1024"]
    return args


def _popen_hidden(cmd: list[str], *, cwd: str) -> subprocess.Popen:
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def _kill_port(port: int) -> None:
    if os.name != "nt":
        return
    try:
        import psutil
    except ImportError:
        return
    for conn in psutil.net_connections(kind="inet"):
        if conn.status == "LISTEN" and conn.laddr.port == port and conn.pid:
            try:
                psutil.Process(conn.pid).kill()
            except Exception:
                pass


def start_llama(*, force: bool = True, model_key: str | None = None) -> tuple[bool, str]:
    with _LOCK:
        port = cfg.llama_port()
        key = model_key or cfg.get_selected_model_key()
        models = cfg.models_registry()
        expected = model_alias_for_key(key) if key in models else None
        label = str(models.get(key, {}).get("label") or key)

        if is_llama_ready(expected):
            return True, f"模型已就绪: {label}"

        if is_port_open(port):
            if not force:
                # 端口开了但未就绪：继续等待，不重复启动
                return wait_until_ready(expected_alias=expected, label=label)
            stop_llama()
            time.sleep(1.0)

        exe = cfg.llama_server_exe()
        if not exe or not os.path.isfile(exe):
            return False, f"找不到 llama-server，请在 config.json 设置 llama_server_exe: {exe}"

        workdir = cfg.llama_dir() or os.path.dirname(exe)
        try:
            args = _build_args(model_key)
        except (ValueError, FileNotFoundError) as exc:
            return False, str(exc)

        try:
            _popen_hidden([exe, *args], cwd=workdir)
        except Exception as exc:
            return False, f"启动失败: {exc}"

        return wait_until_ready(expected_alias=expected, label=label)


def stop_llama() -> tuple[bool, str]:
    with _LOCK:
        port = cfg.llama_port()
        if not is_port_open(port):
            return True, "Llama 未运行"
        _kill_port(port)
        time.sleep(0.8)
        if is_port_open(port):
            return False, f"未能停止 :{port} 上的进程（可安装 psutil 或手动结束 llama-server）"
        return True, "已停止 Llama"


def restart_llama(model_key: str | None = None) -> tuple[bool, str]:
    with _LOCK:
        if model_key is not None and not set_model(model_key):
            return False, f"未知模型: {model_key}"
        stop_llama()
        time.sleep(0.5)
        return start_llama(force=True, model_key=model_key)


def model_alias_for_key(model_key: str) -> str:
    models = cfg.models_registry()
    m = models.get(model_key) or {}
    return str(m.get("alias") or model_key)


def get_loaded_model_alias() -> str | None:
    """查询 llama-server 当前加载的模型 alias（/v1/models）。"""
    if not is_port_open(cfg.llama_port()):
        return None
    code, data = _http_get_json("/v1/models", timeout=3.0)
    if code != 200 or not isinstance(data, dict):
        return None
    items = data.get("data") or []
    if items:
        return str(items[0].get("id") or "").strip() or None
    return None


def ensure_model_loaded(model_key: str | None = None) -> tuple[bool, str]:
    """若所选模型未加载，则自动通过 llama-server 启停加载，并阻塞到真正就绪。"""
    with _LOCK:
        key = (model_key or cfg.get_selected_model_key() or "").strip()
        models = cfg.models_registry()
        if not key or key.startswith("（") or key not in models:
            return False, "请先在 config.json 的 models 中配置模型"
        if not set_model(key):
            return False, f"未知模型: {key}"

        cfg.apply_llama_env(key)
        expected = model_alias_for_key(key)
        label = str(models[key].get("label") or key)

        if is_llama_ready(expected):
            return True, f"模型已就绪: {label}"

        # 端口开着但模型不对 / 未就绪 → 重启到目标模型
        if is_port_open(cfg.llama_port()):
            loaded = get_loaded_model_alias()
            if loaded and loaded != expected:
                ok, msg = restart_llama(key)
                return ok, msg if ok else f"切换模型失败: {msg}"
            # 同模型仍在加载：只等待
            if loaded == expected or loaded is None:
                ok, msg = wait_until_ready(expected_alias=expected, label=label)
                if ok:
                    return ok, msg
                # 等待失败再强制重启一次
                ok, msg = restart_llama(key)
                return ok, msg if ok else f"加载模型失败: {msg}"

        ok, msg = start_llama(force=True, model_key=key)
        return ok, msg if ok else f"加载模型失败: {msg}"
