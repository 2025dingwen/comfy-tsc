# -*- coding: utf-8 -*-
"""按风格生成提示词（内置 prompt_writer，无需 MCP）。"""

from __future__ import annotations

import os

import numpy as np
from PIL import Image

from ..lib import prompt_utils as pu
from ..lib.generate_engine import generate_prompt


class TSCPromptWriterGenerate:
    """选定风格与主题，本地调用 Llama 生成提示词。"""

    CATEGORY = "TSC/提示词"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "status")
    FUNCTION = "generate"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        labels, _ = pu.style_combo_options()
        if not labels:
            labels = ["（风格加载失败，请检查插件安装）"]
        default = next(
            (lb for lb in labels if "gc-minimal-zine-poster" in lb),
            labels[0],
        )
        return {
            "required": {
                "style": (labels, {"default": default}),
                "theme": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "dynamicPrompts": False,
                    },
                ),
                "aspect_ratio": (list(pu.ASPECT_OPTIONS), {"default": "9:16 (Portrait Widescreen)"}),
            },
            "optional": {
                "reference_image": ("IMAGE",),
            },
        }

    def generate(self, style: str, theme: str, aspect_ratio: str, reference_image=None):
        labels, id_by_label = pu.style_combo_options()
        style_id = id_by_label.get(style.strip(), "")
        if not style_id:
            if "（" in style and style.endswith("）"):
                style_id = style.rsplit("（", 1)[-1].rstrip("）")
            else:
                style_id = style.strip()

        aspect = pu.parse_aspect_label(aspect_ratio)
        theme = (theme or "").strip()

        image_path = ""
        if reference_image is not None:
            image_path = self._save_reference_image(reference_image)

        if not style_id or style_id.startswith("（"):
            return ("", "请先选择有效风格。")

        if not theme and not (style_id in ("ltx-video", "ink-editorial") and image_path):
            return ("", "请填写主题/画面描述，或为墨线编辑插画 / ltx-video 提供参考图。")

        if image_path:
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
            theme = f"{theme}\n\n【首帧参考图】{image_path}\n{hint}".strip()

        try:
            data = generate_prompt(style_id, theme, aspect_ratio=aspect)
        except Exception as exc:
            err = str(exc) or type(exc).__name__
            return ("", f"生成失败：{err}\n请确认 config.json 中 Llama 已配置且推理服务 (1233) 已启动。")

        if data.get("status") == "error":
            return ("", str(data.get("message") or "生成失败"))

        text = ""
        for key in ("display", "output", "prompt", "content"):
            if data.get(key):
                text = str(data[key]).strip()
                break
        if not text:
            import json

            text = json.dumps(data, ensure_ascii=False, indent=2)

        body = pu.extract_prompt_body(text)
        resolved = data.get("resolved_style") or style_id
        return (body, f"完成 · {resolved}")

    @staticmethod
    def _save_reference_image(image_tensor) -> str:
        import tempfile

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
