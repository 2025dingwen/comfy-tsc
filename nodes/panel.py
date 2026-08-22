# -*- coding: utf-8 -*-
"""统一控制面板节点：模型 + 风格生成 + 收藏。

按钮在前端节点内调用 API（不排队整图）；
点击 ComfyUI「运行」时：若 result_prompt 已有内容则直接输出，否则自动加载模型并生成。
"""

from __future__ import annotations

from ..lib import favorites as fav
from ..lib import llama_control as lc
from ..lib import prompt_utils as pu
from ..lib import service as svc

_EMPTY_FAV = "-"
_EMPTY_MARKERS = {_EMPTY_FAV, "（暂无收藏）", "(暂无收藏)", ""}


class TSCPromptWriterPanel:
    """提示词生成器控制面板（集合模型/生成/收藏）。"""

    CATEGORY = "TSC/提示词"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "status")
    FUNCTION = "run"
    OUTPUT_NODE = True
    OUTPUT_FORMAT = ""

    @classmethod
    def INPUT_TYPES(cls):
        style_labels, _ = pu.style_combo_options()
        if not style_labels:
            style_labels = ["（风格加载失败）"]
        default_style = next(
            (lb for lb in style_labels if "gc-minimal-zine-poster" in lb),
            style_labels[0],
        )

        models = lc.get_model_labels() or ["（请在 config.json 配置模型）"]
        selected = lc.get_selected_model()
        default_model = models[0]
        keys = lc.get_model_keys()
        if selected and selected in keys:
            idx = keys.index(selected)
            if idx < len(models):
                default_model = models[idx]

        names = fav.favorite_names()
        fav_options = [_EMPTY_FAV] + names

        return {
            "required": {
                "model": (models, {"default": default_model}),
                "style": (style_labels, {"default": default_style}),
                "theme": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "dynamicPrompts": False,
                        "placeholder": "主题 / 画面描述",
                    },
                ),
                "aspect_ratio": (
                    list(pu.ASPECT_OPTIONS),
                    {"default": "9:16 (Portrait Widescreen)"},
                ),
                "favorite": (fav_options, {"default": _EMPTY_FAV}),
                "result_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "dynamicPrompts": False,
                        "placeholder": "可先点「生成提示词」预览并修改；留空则运行工作流时自动生成",
                    },
                ),
            },
            "optional": {
                "reference_image": ("IMAGE",),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, input_types=None, **kwargs):
        return True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def run(
        self,
        model: str,
        style: str,
        theme: str,
        aspect_ratio: str,
        favorite: str,
        result_prompt: str,
        reference_image=None,
        **_kwargs,
    ):
        fav_ui = [_EMPTY_FAV] + fav.favorite_names()
        existing = (result_prompt or "").strip()
        if existing in _EMPTY_MARKERS:
            existing = ""

        # 已有可编辑结果 → 直接走工作流，不再重新生成
        if existing:
            if self.OUTPUT_FORMAT == "ideogram4":
                prompt_out = pu.json_prompt_for_next_node(existing) or existing
            else:
                prompt_out = pu.english_prompt_body(existing) or existing
            status = "使用节点内已有提示词（未重新生成）"
            return {
                "ui": {
                    "text": [status],
                    "favorites": [fav_ui],
                    "result_prompt": [existing],
                },
                "result": (prompt_out, status),
            }

        # 结果为空 → 运行工作流时自动加载模型并生成
        r = svc.do_generate(
            style=style,
            theme=theme,
            aspect_ratio=aspect_ratio,
            reference_image=reference_image,
            model=model,
            auto_favorite=True,
            output_format=self.OUTPUT_FORMAT,
        )
        prompt = r.get("prompt") or ""
        status = r.get("status") or ""
        fav_ui = [_EMPTY_FAV] + (r.get("favorites") or fav.favorite_names())
        if not r.get("ok"):
            raise RuntimeError(status or "提示词生成失败")
        prompt_out = (
            pu.json_prompt_for_next_node(prompt) or prompt
            if self.OUTPUT_FORMAT == "ideogram4"
            else prompt
        )
        return {
            "ui": {
                "text": [status],
                "favorites": [fav_ui],
                "result_prompt": [prompt],
            },
            "result": (prompt_out, status),
        }


class TSCPromptWriterPanelIdeogram4(TSCPromptWriterPanel):
    """与原控制面板相同，各风格结果一律输出 Ideogram4 ArtPrompt JSON。"""

    OUTPUT_FORMAT = "ideogram4"
