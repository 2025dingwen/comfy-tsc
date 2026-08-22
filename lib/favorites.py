# -*- coding: utf-8 -*-
"""提示词收藏 / 生成历史：持久化到插件 data/ 目录。"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_PLUGIN_ROOT, "data")
_FAVORITES_PATH = os.path.join(_DATA_DIR, "favorites.json")
_MAX_HISTORY = 200


def _ensure_data_dir() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)


def _load_raw() -> dict:
    _ensure_data_dir()
    if not os.path.isfile(_FAVORITES_PATH):
        return {"items": []}
    try:
        with open(_FAVORITES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data
    except Exception:
        pass
    return {"items": []}


def _save_raw(data: dict) -> None:
    _ensure_data_dir()
    with open(_FAVORITES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_favorites() -> list[dict]:
    return list(_load_raw().get("items") or [])


def favorite_names() -> list[str]:
    names: list[str] = []
    for item in list_favorites():
        name = str(item.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def get_favorite(name: str) -> dict | None:
    name = (name or "").strip()
    for item in list_favorites():
        if str(item.get("name") or "").strip() == name:
            return item
    return None


def save_favorite(
    *,
    name: str,
    prompt: str,
    style: str = "",
    theme: str = "",
    prepend: bool = False,
) -> tuple[bool, str]:
    name = (name or "").strip()
    prompt = (prompt or "").strip()
    if not name:
        return False, "收藏名称不能为空"
    if not prompt:
        return False, "提示词内容不能为空"

    data = _load_raw()
    items: list[dict] = data.setdefault("items", [])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "id": str(uuid.uuid4()),
        "name": name,
        "style": style,
        "theme": theme,
        "prompt": prompt,
        "created_at": now,
        "updated_at": now,
    }
    replaced = False
    for i, old in enumerate(items):
        if str(old.get("name") or "").strip() == name:
            entry["id"] = old.get("id") or entry["id"]
            entry["created_at"] = old.get("created_at") or now
            items[i] = entry
            replaced = True
            break
    if not replaced:
        if prepend:
            items.insert(0, entry)
        else:
            items.append(entry)
    if len(items) > _MAX_HISTORY:
        data["items"] = items[:_MAX_HISTORY]
    else:
        data["items"] = items
    _save_raw(data)
    verb = "已更新" if replaced else "已收藏"
    return True, f"{verb}：{name}"


def _short_theme(theme: str, limit: int = 28) -> str:
    text = re.sub(r"\s+", " ", (theme or "").strip())
    # 去掉内部附带的参考图路径说明
    if "【首帧参考图】" in text:
        text = text.split("【首帧参考图】", 1)[0].strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def auto_save_history(
    *,
    prompt: str,
    style: str = "",
    theme: str = "",
) -> tuple[bool, str]:
    """每次成功生成后自动写入历史收藏（最新在前）。"""
    prompt = (prompt or "").strip()
    if not prompt:
        return False, "空提示词，跳过自动收藏"
    stamp = datetime.now().strftime("%m-%d %H:%M:%S")
    style_part = (style or "").strip() or "unknown"
    if "（" in style_part and style_part.endswith("）"):
        style_part = style_part.rsplit("（", 1)[-1].rstrip("）")
    theme_part = _short_theme(theme)
    name = f"{stamp} · {style_part}"
    if theme_part:
        name = f"{name} · {theme_part}"
    return save_favorite(
        name=name,
        prompt=prompt,
        style=style,
        theme=theme,
        prepend=True,
    )


def delete_favorite(name: str) -> tuple[bool, str]:
    name = (name or "").strip()
    if not name:
        return False, "请指定要删除的收藏名称"
    data = _load_raw()
    items = data.get("items") or []
    new_items = [x for x in items if str(x.get("name") or "").strip() != name]
    if len(new_items) == len(items):
        return False, f"未找到收藏：{name}"
    data["items"] = new_items
    _save_raw(data)
    return True, f"已删除：{name}"
