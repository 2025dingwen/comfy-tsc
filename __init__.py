# -*- coding: utf-8 -*-
"""
comfy-tsc — ComfyUI 自包含提示词生成器插件

安装：复制到 ComfyUI/custom_nodes/ → install.bat → 编辑 config.json → 重启 ComfyUI
右下角「词」按钮打开提示词生成器面板（与控制台界面一致）。
"""

from .nodes.panel import TSCPromptWriterPanel, TSCPromptWriterPanelIdeogram4
from .nodes.model_loader import TSCPromptWriterModelLoader
from .nodes.generate import TSCPromptWriterGenerate
from .nodes.favorites import TSCPromptWriterFavoriteSave, TSCPromptWriterFavoriteLoad

NODE_CLASS_MAPPINGS = {
    "TSCPromptWriterPanel": TSCPromptWriterPanel,
    "TSCPromptWriterPanelIdeogram4": TSCPromptWriterPanelIdeogram4,
    "TSCPromptWriterModelLoader": TSCPromptWriterModelLoader,
    "TSCPromptWriterGenerate": TSCPromptWriterGenerate,
    "TSCPromptWriterFavoriteSave": TSCPromptWriterFavoriteSave,
    "TSCPromptWriterFavoriteLoad": TSCPromptWriterFavoriteLoad,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TSCPromptWriterPanel": "TSC 提示词生成器（控制面板）",
    "TSCPromptWriterPanelIdeogram4": "TSC 提示词生成器（Ideogram4 控制面板）",
    "TSCPromptWriterModelLoader": "TSC 提示词 · Llama 模型",
    "TSCPromptWriterGenerate": "TSC 提示词 · 生成",
    "TSCPromptWriterFavoriteSave": "TSC 提示词 · 收藏",
    "TSCPromptWriterFavoriteLoad": "TSC 提示词 · 读取收藏",
}

WEB_DIRECTORY = "./web/js"


def _try_register_routes() -> bool:
    try:
        from .server_routes import register_routes

        return bool(register_routes())
    except Exception as exc:
        print(f"[comfy-tsc] panel API not ready: {exc}")
        return False


if not _try_register_routes():
    # ComfyUI 启动早期可能还没有 PromptServer.instance，延后到实例创建后注册
    try:
        import server as _comfy_server

        if not getattr(_comfy_server.PromptServer, "_tsc_prompt_hooked", False):
            _orig = _comfy_server.PromptServer.__init__

            def _init_and_register(self, *args, **kwargs):
                _orig(self, *args, **kwargs)
                try:
                    from .server_routes import register_routes

                    register_routes()
                except Exception as exc:
                    print(f"[comfy-tsc] deferred panel API failed: {exc}")

            _comfy_server.PromptServer.__init__ = _init_and_register
            _comfy_server.PromptServer._tsc_prompt_hooked = True
    except Exception as exc:
        print(f"[comfy-tsc] could not hook PromptServer: {exc}")

try:
    from .lib.generate_engine import warmup

    warmup()
except Exception as _warm_exc:
    print(f"[comfy-tsc] warmup skipped: {_warm_exc}")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
