# -*- coding: utf-8 -*-
"""统一业务：生成 / 模型 / 收藏（节点与面板 API 共用）。"""

from __future__ import annotations

import json
import os
import tempfile

import numpy as np
from PIL import Image

from . import favorites as fav
from . import llama_control as lc
from . import prompt_utils as pu
from .config import apply_llama_env
from .generate_engine import generate_prompt
from prompt_writer.craft_llm import translate_prompt_to_zh, wrap_as_ideogram4_json


def resolve_style_id(style: str) -> str:
    style = (style or "").strip()
    if "（" in style and style.endswith("）"):
        return style.rsplit("（", 1)[-1].rstrip("）")
    labels, id_by_label = pu.style_combo_options()
    if style in id_by_label:
        return id_by_label[style]
    return style


def save_reference_image(image_tensor) -> str:
    try:
        import folder_paths

        temp_dir = folder_paths.get_temp_directory()
    except ImportError:
        temp_dir = tempfile.gettempdir()
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, "tsc_prompt_writer_ref.png")
    arr = image_tensor[0].cpu().numpy()
    arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    Image.fromarray(arr).save(path, format="PNG")
    return path


def save_reference_image_from_bytes(data: bytes, filename: str = "ref.png") -> str:
    try:
        import folder_paths

        temp_dir = folder_paths.get_temp_directory()
    except ImportError:
        temp_dir = tempfile.gettempdir()
    os.makedirs(temp_dir, exist_ok=True)
    ext = os.path.splitext(filename)[1] or ".png"
    path = os.path.join(temp_dir, f"tsc_prompt_writer_ref{ext}")
    with open(path, "wb") as f:
        f.write(data)
    return path


def allows_image_only(style_id: str) -> bool:
    return style_id in ("ltx-video", "ink-editorial")


def build_theme_with_image(theme: str, style_id: str, image_path: str) -> str:
    theme = (theme or "").strip()
    if not image_path:
        return theme
    if style_id == "ink-editorial" and not theme:
        hint = (
            "（墨线转译：先视觉理解这张参考图的主体、姿态、服饰、互动物体与裁切；"
            "再用墨线编辑插画 DNA 还原。锁定图中的人/物/姿态/接触点，不要另编故事。）"
        )
    elif style_id == "ink-editorial":
        hint = (
            "（墨线转译：先视觉理解参考图，再用墨线编辑插画 DNA 还原；"
            "以参考图为主体，用户文字仅作修正。）"
        )
    elif style_id == "ltx-video" and not theme:
        hint = (
            "（图生视频：视频首帧必须是这张图的精确复刻。无主题描述："
            "请先视觉理解图片，再规划一个从原构图出发的简单运镜。）"
        )
    elif style_id == "ltx-video":
        hint = (
            "（图生视频：视频首帧必须是这张图的精确复刻，"
            "请按用户描述写从首帧开始接下来发生什么。）"
        )
    else:
        hint = (
            "（图生视频：视频首帧必须是这张图的精确复刻，"
            "请按用户描述锁定图中的人物/服装/背景。）"
        )
    return f"{theme}\n\n【首帧参考图】{image_path}\n{hint}".strip()


def ensure_model(model: str) -> dict:
    """按面板/节点所选模型，确保 llama-server 已加载对应 GGUF。"""
    model_key = lc.key_from_label(model)
    ok, msg = lc.ensure_model_loaded(model_key)
    return {"ok": ok, "status": msg, "model_key": lc.get_selected_model() or model_key}


def do_generate(
    *,
    style: str,
    theme: str,
    aspect_ratio: str = "",
    image_path: str = "",
    reference_image=None,
    model: str = "",
    auto_favorite: bool = True,
    output_format: str = "",
) -> dict:
    # 生成前阻塞直到所选模型真正可推理，避免工作流带着空 prompt 往下跑
    if (model or "").strip():
        load_r = ensure_model(model)
    else:
        selected = lc.get_selected_model()
        if selected:
            ok, msg = lc.ensure_model_loaded(selected)
            load_r = {"ok": ok, "status": msg, "model_key": selected}
        else:
            labels = lc.get_model_labels()
            load_r = (
                ensure_model(labels[0])
                if labels
                else {"ok": False, "status": "请先在 config.json 配置 models", "model_key": ""}
            )
    if not load_r.get("ok"):
        return {
            "ok": False,
            "prompt": "",
            "status": load_r.get("status") or "模型未就绪",
            "style_id": "",
        }

    style_id = resolve_style_id(style)
    aspect = pu.parse_aspect_label(aspect_ratio)
    theme = (theme or "").strip()
    theme_for_fav = theme

    if reference_image is not None and not image_path:
        image_path = save_reference_image(reference_image)

    if not style_id or style_id.startswith("（"):
        return {"ok": False, "prompt": "", "status": "请先选择有效风格。", "style_id": style_id}

    if not theme and not (allows_image_only(style_id) and image_path):
        return {
            "ok": False,
            "prompt": "",
            "status": "请填写主题/画面描述，或为墨线编辑插画 / ltx-video 提供参考图。",
            "style_id": style_id,
        }

    theme = build_theme_with_image(theme, style_id, image_path)

    try:
        data = generate_prompt(style_id, theme, aspect_ratio=aspect)
    except Exception as exc:
        err = str(exc) or type(exc).__name__
        return {
            "ok": False,
            "prompt": "",
            "status": f"生成失败：{err}\n请确认 Llama 推理已启动（端口 1233）。",
            "style_id": style_id,
        }

    if data.get("status") == "error":
        return {
            "ok": False,
            "prompt": "",
            "status": str(data.get("message") or "生成失败"),
            "style_id": style_id,
        }

    text = ""
    for key in ("display", "output", "prompt", "content"):
        if data.get(key):
            text = str(data[key]).strip()
            break
    if not text:
        text = json.dumps(data, ensure_ascii=False, indent=2)

    body = pu.extract_prompt_body(text)
    resolved = data.get("resolved_style") or style_id

    if (output_format or "").strip().lower() in {"ideogram4", "ideogram_json", "json"}:
        src = str(data.get("prompt") or data.get("content") or body).strip() or body
        wrapped = wrap_as_ideogram4_json(
            src, aspect_ratio=aspect or "3:4", style_id=resolved
        )
        if wrapped.get("status") != "success":
            return {
                "ok": False,
                "prompt": "",
                "status": str(wrapped.get("message") or "转为 Ideogram4 JSON 失败"),
                "style_id": resolved,
            }
        body = str(wrapped.get("prompt") or "").strip()
        status = f"完成 · {resolved} · Ideogram4 JSON"
    else:
        status = f"完成 · {resolved} · 已去除头尾标记"

    fav_msg = ""
    if auto_favorite and body:
        ok_fav, fav_msg = fav.auto_save_history(
            prompt=body,
            style=resolved,
            theme=theme_for_fav,
        )
        if ok_fav:
            status = f"{status} · 已自动收藏"

    return {
        "ok": True,
        "prompt": body,
        "status": status,
        "style_id": resolved,
        "theme": theme,
        "favorite_status": fav_msg,
        "favorites": fav.favorite_names(),
    }


def do_translate(*, text: str, model: str = "") -> dict:
    """把结果栏里的提示词译成中文，原文仍保留在译文标记之前。"""
    src = pu.english_prompt_body(text)
    if not src or src.startswith("正在"):
        return {
            "ok": False,
            "prompt": "",
            "status": "请先生成提示词，再点翻译。",
        }

    if (model or "").strip():
        load_r = ensure_model(model)
    else:
        selected = lc.get_selected_model()
        if selected:
            ok, msg = lc.ensure_model_loaded(selected)
            load_r = {"ok": ok, "status": msg, "model_key": selected}
        else:
            labels = lc.get_model_labels()
            load_r = (
                ensure_model(labels[0])
                if labels
                else {"ok": False, "status": "请先在 config.json 配置 models", "model_key": ""}
            )
    if not load_r.get("ok"):
        return {
            "ok": False,
            "prompt": "",
            "status": load_r.get("status") or "模型未就绪",
        }

    apply_llama_env(load_r.get("model_key") or "")
    try:
        data = translate_prompt_to_zh(src)
    except Exception as exc:
        err = str(exc) or type(exc).__name__
        return {
            "ok": False,
            "prompt": "",
            "status": f"翻译失败：{err}\n请确认 Llama 推理已启动（端口 1233）。",
        }

    if data.get("status") != "success":
        return {
            "ok": False,
            "prompt": "",
            "status": str(data.get("message") or "翻译失败"),
        }

    zh = str(data.get("prompt") or "").strip()
    combined = f"{src}\n\n{pu.CN_TRANSLATION_MARK}\n{zh}"
    return {
        "ok": True,
        "prompt": combined,
        "translation": zh,
        "english": src,
        "status": "已翻译为中文（原文仍保留在上方，工作流只使用英文）",
    }


def do_llama_action(model: str, action: str) -> dict:
    model_key = lc.key_from_label(model)
    messages: list[str] = []

    if action in ("检查状态", "status"):
        st = lc.service_status()
        messages.append(
            f"Llama: {'运行中' if st['llama'] else '未运行'} · "
            f"当前 {lc.get_selected_model() or model_key or '未选'}"
        )
        return {"ok": True, "status": "\n".join(messages), "model_key": model_key}

    if action in ("切换模型并重启 Llama", "restart", "切换并重启", "auto", "ensure"):
        if not model_key or model_key.startswith("（"):
            return {"ok": False, "status": "请先在 config.json 配置 models", "model_key": model_key}
        ok, msg = lc.ensure_model_loaded(model_key)
        return {"ok": ok, "status": msg, "model_key": lc.get_selected_model() or model_key}

    if action in ("加载 Llama 推理", "load", "加载"):
        if model_key and not model_key.startswith("（"):
            ok, msg = lc.ensure_model_loaded(model_key)
        else:
            ok, msg = lc.start_llama(force=True)
        return {"ok": ok, "status": msg, "model_key": lc.get_selected_model() or model_key}

    if action in ("卸载 Llama 推理", "unload", "卸载"):
        ok, msg = lc.stop_llama()
        return {"ok": ok, "status": msg, "model_key": model_key}

    return {"ok": False, "status": f"未知操作: {action}", "model_key": model_key}


def panel_bootstrap() -> dict:
    styles = pu.load_prompt_styles()
    labels, id_by_label = pu.style_combo_options(styles)
    models = lc.get_model_labels()
    selected = lc.get_selected_model()
    default_model = models[0] if models else ""
    keys = lc.get_model_keys()
    if selected and selected in keys:
        idx = keys.index(selected)
        if idx < len(models):
            default_model = models[idx]
    default_style = next(
        (lb for lb in labels if "gc-minimal-zine-poster" in lb),
        labels[0] if labels else "",
    )
    return {
        "styles": labels,
        "style_ids": id_by_label,
        "aspect_ratios": list(pu.ASPECT_OPTIONS),
        "models": models,
        "default_model": default_model,
        "default_style": default_style,
        "favorites": fav.favorite_names(),
        "favorites_detail": fav.list_favorites(),
        "llama": lc.service_status(),
        "selected_model": selected,
    }
