# -*- coding: utf-8 -*-
"""插件配置：Llama 推理地址、模型注册表等（完全自包含，不依赖 ideogram-imag）。"""

from __future__ import annotations

import json
import os

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_PLUGIN_ROOT, "config.json")
_EXAMPLE_PATH = os.path.join(_PLUGIN_ROOT, "config.example.json")
_STATE_PATH = os.path.join(_PLUGIN_ROOT, "data", "llama_model.json")


def plugin_root() -> str:
    return _PLUGIN_ROOT


def _load_file() -> dict:
    for path in (_CONFIG_PATH, _EXAMPLE_PATH):
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def llama_backend_url() -> str:
    env = (os.getenv("LLAMA_BACKEND_URL") or "").strip()
    if env:
        return env.rstrip("/")
    cfg = (_load_file().get("llama_backend_url") or "").strip()
    return (cfg or "http://127.0.0.1:1233").rstrip("/")


def llama_port() -> int:
    cfg = _load_file()
    if "llama_port" in cfg:
        return int(cfg["llama_port"])
    url = llama_backend_url()
    if url.rsplit(":", 1)[-1].isdigit():
        return int(url.rsplit(":", 1)[-1])
    return 1233


def llama_server_exe() -> str:
    env = (os.getenv("LLAMA_SERVER_EXE") or "").strip()
    if env:
        return env
    return (_load_file().get("llama_server_exe") or "").strip()


def llama_dir() -> str:
    env = (os.getenv("LLAMA_DIR") or "").strip()
    if env:
        return env
    return (_load_file().get("llama_dir") or "").strip()


def llama_threads() -> str:
    return str(_load_file().get("llama_threads") or os.getenv("LLAMA_THREADS") or "8")


def models_registry() -> dict[str, dict]:
    cfg = _load_file()
    models = cfg.get("models")
    if isinstance(models, dict) and models:
        return models
    return {}


def get_selected_model_key() -> str:
    env = (os.getenv("LLAMA_MODEL_KEY") or "").strip()
    models = models_registry()
    if env and env in models:
        return env
    _ensure_data_dir()
    if os.path.isfile(_STATE_PATH):
        try:
            with open(_STATE_PATH, encoding="utf-8") as f:
                key = str(json.load(f).get("selected") or "").strip()
            if key in models:
                return key
        except Exception:
            pass
    keys = list(models.keys())
    return keys[0] if keys else ""


def set_selected_model_key(key: str) -> None:
    _ensure_data_dir()
    with open(_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"selected": key}, f, ensure_ascii=False, indent=2)


def apply_llama_env(model_key: str | None = None) -> None:
    """让 bundled prompt_writer.craft_llm 读到当前配置。"""
    cfg = _load_file()
    os.environ["LLAMA_BACKEND_URL"] = llama_backend_url()
    key = (model_key or get_selected_model_key() or "").strip()
    models = models_registry()
    alias = str(models.get(key, {}).get("alias") or key or "qwen3.6-27b")
    os.environ["PROMPT_WRITER_MODEL"] = alias
    max_tok = cfg.get("craft_max_tokens")
    if max_tok is not None and "PROMPT_WRITER_CRAFT_MAX_TOKENS" not in os.environ:
        os.environ["PROMPT_WRITER_CRAFT_MAX_TOKENS"] = str(int(max_tok))


def _ensure_data_dir() -> None:
    os.makedirs(os.path.join(_PLUGIN_ROOT, "data"), exist_ok=True)
