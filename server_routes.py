# -*- coding: utf-8 -*-
"""HTTP API：供前端控制面板调用。"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger("comfy-tsc")


def register_routes() -> bool:
    try:
        from aiohttp import web
        from server import PromptServer
    except Exception as exc:
        logger.warning("PromptServer 不可用，跳过 TSC 面板 API: %s", exc)
        return False

    routes = PromptServer.instance.routes
    prefix = "/tsc_prompt"

    from .lib import favorites as fav
    from .lib import llama_control as lc
    from .lib import service as svc
    from .lib.prompt_utils import load_style_usage

    @routes.get(f"{prefix}/bootstrap")
    async def bootstrap(_request):
        try:
            return web.json_response({"ok": True, **svc.panel_bootstrap()})
        except Exception as exc:
            return web.json_response({"ok": False, "error": str(exc)}, status=500)

    @routes.get(f"{prefix}/styles")
    async def styles(_request):
        from .lib.prompt_utils import refresh_prompt_styles

        refresh_prompt_styles()
        data = svc.panel_bootstrap()
        return web.json_response({"ok": True, "styles": data["styles"], "default_style": data["default_style"]})

    @routes.get(f"{prefix}/usage")
    async def usage(request):
        sid = request.rel_url.query.get("style_id", "").strip()
        text = load_style_usage(sid) if sid else ""
        return web.json_response({"ok": bool(text.strip()), "style_id": sid, "text": text})

    @routes.get(f"{prefix}/favorites")
    async def favorites_list(_request):
        return web.json_response(
            {"ok": True, "names": fav.favorite_names(), "items": fav.list_favorites()}
        )

    @routes.post(f"{prefix}/favorites/save")
    async def favorites_save(request):
        body = await request.json()
        ok, msg = fav.save_favorite(
            name=str(body.get("name") or ""),
            prompt=str(body.get("prompt") or ""),
            style=str(body.get("style") or ""),
            theme=str(body.get("theme") or ""),
        )
        return web.json_response(
            {
                "ok": ok,
                "status": msg,
                "names": fav.favorite_names(),
                "items": fav.list_favorites(),
            }
        )

    @routes.post(f"{prefix}/favorites/delete")
    async def favorites_delete(request):
        body = await request.json()
        ok, msg = fav.delete_favorite(str(body.get("name") or ""))
        return web.json_response(
            {
                "ok": ok,
                "status": msg,
                "names": fav.favorite_names(),
                "items": fav.list_favorites(),
            }
        )

    @routes.post(f"{prefix}/llama")
    async def llama_action(request):
        body = await request.json()
        result = await asyncio.to_thread(
            svc.do_llama_action,
            str(body.get("model") or ""),
            str(body.get("action") or "status"),
        )
        result["llama"] = lc.service_status()
        result["models"] = lc.get_model_labels()
        result["selected_model"] = lc.get_selected_model()
        return web.json_response(result)

    @routes.post(f"{prefix}/generate")
    async def generate(request):
        ctype = request.content_type or ""
        image_path = ""
        if "multipart/" in ctype:
            reader = await request.multipart()
            fields = {}
            image_bytes = None
            image_name = "ref.png"
            while True:
                part = await reader.next()
                if part is None:
                    break
                name = part.name or ""
                if name == "image":
                    image_bytes = await part.read(decode=False)
                    image_name = part.filename or "ref.png"
                else:
                    fields[name] = (await part.text()).strip()
            if image_bytes:
                image_path = await asyncio.to_thread(
                    svc.save_reference_image_from_bytes, image_bytes, image_name
                )
            result = await asyncio.to_thread(
                svc.do_generate,
                style=fields.get("style", ""),
                theme=fields.get("theme", ""),
                aspect_ratio=fields.get("aspect_ratio", ""),
                image_path=image_path,
                model=fields.get("model", ""),
                output_format=fields.get("output_format", ""),
            )
        else:
            body = await request.json()
            result = await asyncio.to_thread(
                svc.do_generate,
                style=str(body.get("style") or ""),
                theme=str(body.get("theme") or ""),
                aspect_ratio=str(body.get("aspect_ratio") or ""),
                image_path=str(body.get("image_path") or ""),
                model=str(body.get("model") or ""),
                output_format=str(body.get("output_format") or ""),
            )
        return web.json_response(result)

    @routes.post(f"{prefix}/translate")
    async def translate(request):
        body = await request.json()
        result = await asyncio.to_thread(
            svc.do_translate,
            text=str(body.get("text") or body.get("prompt") or ""),
            model=str(body.get("model") or ""),
        )
        return web.json_response(result)

    logger.info("TSC Prompt panel API registered at %s/*", prefix)
    return True
