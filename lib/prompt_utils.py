# -*- coding: utf-8 -*-
"""提示词工具：风格列表、正文提取等。"""

from __future__ import annotations

import re

from .generate_engine import list_ready_styles

_PROMPT_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
CN_TRANSLATION_MARK = "【中文翻译】"


def english_prompt_body(text: str) -> str:
    """结果栏可能附带中文译文；工作流只取译文标记之前的原文。"""
    t = (text or "").strip()
    i = t.find(CN_TRANSLATION_MARK)
    if i >= 0:
        t = t[:i].strip()
    return t

_STYLE_CACHE: list[dict] | None = None

ASPECT_OPTIONS = (
    "自动（按风格题材）",
    "1:1 (Square)",
    "2:3 (Portrait Photo)",
    "3:2 (Photo)",
    "3:4 (Portrait Standard)",
    "4:3 (Standard)",
    "9:16 (Portrait Widescreen)",
    "16:9 (Widescreen)",
)


def json_prompt_for_next_node(text: str) -> str:
    """Ideogram4 面板：去掉中文译文和代码围栏，只把 JSON 交给下一节点。"""
    t = english_prompt_body(text)
    m = _PROMPT_FENCE_RE.search(t)
    if m:
        inner = m.group(1).strip()
        if inner.startswith("{") and "high_level_description" in inner:
            return inner
    return t


def extract_prompt_body(text: str) -> str:
    if not text:
        return text
    m = _PROMPT_FENCE_RE.search(text)
    if m:
        body = m.group(1).strip()
        if len(body) >= 20:
            return body
    return re.sub(r"\*\*(.*?)\*\*", r"\1", text).strip()


def parse_aspect_label(label: str) -> str:
    label = (label or "").strip()
    return "" if label.startswith("自动") else label.split(" ", 1)[0]


def load_prompt_styles() -> list[dict]:
    global _STYLE_CACHE
    if _STYLE_CACHE is not None:
        return _STYLE_CACHE
    try:
        _STYLE_CACHE = list_ready_styles()
        return _STYLE_CACHE
    except Exception:
        return []


def refresh_prompt_styles() -> list[dict]:
    global _STYLE_CACHE
    _STYLE_CACHE = None
    return load_prompt_styles()


def style_combo_options(styles: list[dict] | None = None) -> tuple[list[str], dict[str, str]]:
    styles = styles or load_prompt_styles()
    labels: list[str] = []
    id_by_label: dict[str, str] = {}
    for s in styles:
        sid = str(s.get("id") or "")
        name = str(s.get("name") or sid)
        label = f"{name}（{sid}）"
        labels.append(label)
        id_by_label[label] = sid
    return labels, id_by_label


def load_style_usage(style_id: str) -> str:
    try:
        from prompt_writer.loader import load_style_usage as _load

        return _load(style_id) or ""
    except Exception:
        return ""
