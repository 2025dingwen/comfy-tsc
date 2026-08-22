# -*- coding: utf-8 -*-
"""收藏 / 读取已生成的提示词。"""

from __future__ import annotations

from ..lib import favorites as fav


class TSCPromptWriterFavoriteSave:
    """将提示词收藏到本地，供工作流再次选用。"""

    CATEGORY = "TSC/提示词"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "status")
    FUNCTION = "save"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "name": ("STRING", {"default": "我的提示词", "multiline": False}),
                "prompt": (
                    "STRING",
                    {"default": "", "multiline": True, "dynamicPrompts": False},
                ),
                "style": ("STRING", {"default": "", "multiline": False}),
                "theme": (
                    "STRING",
                    {"default": "", "multiline": True, "dynamicPrompts": False},
                ),
            },
        }

    def save(self, name: str, prompt: str, style: str, theme: str):
        ok, msg = fav.save_favorite(name=name, prompt=prompt, style=style, theme=theme)
        return (prompt if ok else "", msg)


class TSCPromptWriterFavoriteLoad:
    """从收藏列表加载已保存的提示词。"""

    CATEGORY = "TSC/提示词"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt", "style", "theme")
    FUNCTION = "load"

    ACTIONS = ["加载收藏", "删除收藏", "列出全部"]

    @classmethod
    def INPUT_TYPES(cls):
        names = fav.favorite_names() or ["（暂无收藏）"]
        return {
            "required": {
                "favorite": (names, {"default": names[0]}),
                "action": (cls.ACTIONS, {"default": "加载收藏"}),
            },
        }

    def load(self, favorite: str, action: str):
        if action == "列出全部":
            items = fav.list_favorites()
            if not items:
                return ("", "", "暂无收藏")
            lines = []
            for item in items:
                lines.append(
                    f"- {item.get('name')} [{item.get('style', '')}] "
                    f"({item.get('updated_at', '')})"
                )
            return ("\n".join(lines), "", f"共 {len(items)} 条收藏")

        if action == "删除收藏":
            ok, msg = fav.delete_favorite(favorite)
            return ("", "", msg)

        item = fav.get_favorite(favorite)
        if not item:
            return ("", "", f"未找到收藏：{favorite}")
        return (
            str(item.get("prompt") or ""),
            str(item.get("style") or ""),
            str(item.get("theme") or ""),
        )
