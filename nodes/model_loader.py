# -*- coding: utf-8 -*-
"""Llama 模型选择与推理服务加载。"""

from __future__ import annotations

from ..lib import llama_control as lc


class TSCPromptWriterModelLoader:
    """选择 Llama 模型并加载/卸载本地推理服务。"""

    CATEGORY = "TSC/提示词"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("status", "model_key")
    FUNCTION = "run"
    OUTPUT_NODE = True

    ACTIONS = [
        "检查状态",
        "加载 Llama 推理",
        "卸载 Llama 推理",
        "切换模型并重启 Llama",
    ]

    @classmethod
    def INPUT_TYPES(cls):
        labels = lc.get_model_labels()
        if not labels:
            labels = ["（请在 config.json 的 models 中配置模型）"]
        selected = lc.get_selected_model()
        default_label = labels[0]
        keys = lc.get_model_keys()
        if selected and selected in keys:
            idx = keys.index(selected)
            if idx < len(labels):
                default_label = labels[idx]

        return {
            "required": {
                "model": (labels, {"default": default_label}),
                "action": (cls.ACTIONS, {"default": "检查状态"}),
            },
        }

    def run(self, model: str, action: str):
        model_key = lc.key_from_label(model)
        messages: list[str] = []

        if action == "检查状态":
            st = lc.service_status()
            port_msg = "运行中" if st["llama"] else "未运行"
            messages.append(f"Llama ({lc.get_selected_model() or model_key}): {port_msg}")
            messages.append(f"当前选择: {model}")
            if not lc.get_model_keys():
                messages.append("提示: 编辑 config.json → models 添加你的 .gguf 模型路径")
            return ("\n".join(messages), model_key)

        if action in ("切换模型并重启 Llama",):
            if not model_key or model_key.startswith("（"):
                return ("请先在 config.json 配置 models", model_key)
            ok, msg = lc.ensure_model_loaded(model_key)
            messages.append(msg)
            return ("\n".join(messages), lc.get_selected_model() or model_key)

        if action == "加载 Llama 推理":
            if model_key and not model_key.startswith("（"):
                ok, msg = lc.ensure_model_loaded(model_key)
            else:
                ok, msg = lc.start_llama(force=True)
            messages.append(msg)

        if action == "卸载 Llama 推理":
            ok, msg = lc.stop_llama()
            messages.append(msg)

        st = lc.service_status()
        messages.append(f"状态 → Llama: {'运行中' if st['llama'] else '未运行'}")
        return ("\n".join(messages), lc.get_selected_model() or model_key)
