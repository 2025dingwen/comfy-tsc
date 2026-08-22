# -*- coding: utf-8 -*-
"""内置 prompt_writer 直接生成（无需 MCP 服务）。"""

from __future__ import annotations

import sys

from .config import apply_llama_env, plugin_root

_PLUGIN_ROOT = plugin_root()
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

apply_llama_env()

import prompt_writer as pw  # noqa: E402
from prompt_writer.craft_llm import (  # noqa: E402
    craft_city_architecture_poster,
    craft_classical_poetry_json,
    craft_cys_migration,
    craft_five_paragraph,
    craft_flat_ad_poster,
    craft_gpt_image2,
    craft_heavenly_palace,
    craft_ideogram4_json,
    craft_iron_slag,
    craft_ink_editorial,
    craft_ltx_video,
    craft_museum_print_illustration,
    craft_portrait_prompt,
    craft_seedance_video,
    craft_zine_poster,
)
from prompt_writer.router import resolve_portrait_route, resolve_zine_route  # noqa: E402

_CRAFT = {
    "craft_classical_poetry_json": craft_classical_poetry_json,
    "craft_ideogram4_json": craft_ideogram4_json,
    "craft_zine_poster": craft_zine_poster,
    "craft_cys_migration": craft_cys_migration,
    "craft_gpt_image2": craft_gpt_image2,
    "craft_flat_ad_poster": craft_flat_ad_poster,
    "craft_city_architecture_poster": craft_city_architecture_poster,
    "craft_ltx_video": craft_ltx_video,
    "craft_seedance_video": craft_seedance_video,
    "craft_heavenly_palace": craft_heavenly_palace,
    "craft_iron_slag": craft_iron_slag,
    "craft_ink_editorial": craft_ink_editorial,
    "craft_museum_print_illustration": craft_museum_print_illustration,
    "craft_portrait_prompt": craft_portrait_prompt,
    "craft_five_paragraph": craft_five_paragraph,
}


def _finish_json_result(result: dict, sid: str, label: str) -> dict:
    result["resolved_style"] = sid
    result["resolved_label"] = label
    if result.get("status") == "success":
        prompt = result.get("prompt") or ""
        display = f"```json\n{prompt}\n```"
        result.update(content=prompt, display=display, output=display)
    return result


def _finish_text_result(result: dict, sid: str, label: str) -> dict:
    result["resolved_style"] = sid
    result["resolved_label"] = label
    if result.get("status") == "success":
        prompt = result.get("prompt") or ""
        result.update(content=prompt, display=prompt, output=prompt)
    return result


def generate_prompt(
    style: str,
    params: str,
    aspect_ratio: str = "",
) -> dict:
    """与 prompt_writer MCP 的 generate action 等价，本地直调。"""
    apply_llama_env()

    raw_style = (style or "").strip().lower()
    if raw_style in {"", "auto", "自动"}:
        sid = pw.resolve_style_from_text(params or "")
    else:
        sid = pw.normalize_style_id(style)

    spec = pw.get_style(sid)
    label = pw.resolve_style_label(sid)
    aspect = aspect_ratio or "3:4"

    if sid == "classical-poetry" or spec.output_kind == "poetry_ideogram_json":
        return _finish_json_result(
            _CRAFT["craft_classical_poetry_json"](params or "", aspect_ratio=aspect),
            sid,
            label,
        )

    if sid == "ideogram4" or spec.output_kind == "ideogram_json":
        return _finish_json_result(
            _CRAFT["craft_ideogram4_json"](params or "", aspect_ratio=aspect),
            sid,
            label,
        )

    if sid == "gc-minimal-zine-poster" or spec.output_kind == "zine_standard_mode":
        route = resolve_zine_route(params or "")
        return _finish_text_result(
            _CRAFT["craft_zine_poster"](params or "", route_style=route),
            sid,
            label,
        )

    if sid == "cys-migration" or spec.output_kind == "cys_nine_section":
        return _finish_text_result(_CRAFT["craft_cys_migration"](params or ""), sid, label)

    if sid == "gpt-image-2" or spec.output_kind == "gpt_image2_prompt":
        return _finish_text_result(_CRAFT["craft_gpt_image2"](params or ""), sid, label)

    if sid == "flat-ad-poster" or spec.output_kind == "flat_ad_poster":
        return _finish_text_result(_CRAFT["craft_flat_ad_poster"](params or ""), sid, label)

    if sid == "city-architecture-poster" or spec.output_kind == "city_architecture_poster":
        return _finish_text_result(
            _CRAFT["craft_city_architecture_poster"](params or ""), sid, label
        )

    if sid == "ltx-video" or spec.output_kind == "ltx_t2v_prompt":
        return _finish_text_result(_CRAFT["craft_ltx_video"](params or ""), sid, label)

    if sid == "seedance-video" or spec.output_kind == "seedance_i2v_prompt":
        return _finish_text_result(_CRAFT["craft_seedance_video"](params or ""), sid, label)

    if sid == "heavenly-palace" or spec.output_kind == "heavenly_palace":
        return _finish_text_result(_CRAFT["craft_heavenly_palace"](params or ""), sid, label)

    if sid == "iron-slag" or spec.output_kind == "iron_slag_prompt":
        return _finish_text_result(
            _CRAFT["craft_iron_slag"](params or "", aspect_ratio=aspect),
            sid,
            label,
        )

    if sid == "ink-editorial" or spec.output_kind == "ink_editorial_prompt":
        return _finish_text_result(
            _CRAFT["craft_ink_editorial"](params or "", aspect_ratio=aspect),
            sid,
            label,
        )

    if sid == "museum-print-illustration" or spec.output_kind == "museum_print_prompt":
        return _finish_text_result(
            _CRAFT["craft_museum_print_illustration"](params or "", aspect_ratio=aspect_ratio or ""),
            sid,
            label,
        )

    if spec.output_kind == "five_paragraph" or sid == "portrait":
        if sid == "portrait":
            route = resolve_portrait_route(params or "")
            result = _CRAFT["craft_portrait_prompt"](params or "", route_style=route)
        else:
            result = _CRAFT["craft_five_paragraph"](sid, params or "")
        return _finish_text_result(result, sid, label)

    bundle = pw.build_generate_bundle(sid, params or "")
    bundle["resolved_style"] = sid
    bundle["resolved_label"] = label
    return bundle


def list_ready_styles() -> list[dict]:
    apply_llama_env()
    return [s for s in pw.list_styles() if (s.get("status") or "") == "ready"]


def warmup() -> None:
    """启动时预加载风格列表与常用 skill 文件，避免首次生成卡顿。"""
    apply_llama_env()
    list_ready_styles()
    from prompt_writer.craft_llm import _read_skill_file

    for rel, limit in (
        ("styles/museum-print-illustration/skill.md", 14000),
        ("styles/museum-print-illustration/schema.md", 4000),
        ("styles/museum-print-illustration/example.md", 8000),
        ("styles/iron-slag/skill.md", 14000),
        ("styles/iron-slag/schema.md", 4000),
        ("styles/iron-slag/example.md", 5000),
        ("styles/ink-editorial/skill.md", 18000),
        ("styles/ink-editorial/schema.md", 5000),
        ("styles/ink-editorial/example.md", 12000),
        ("styles/ink-editorial/translate.md", 6000),
        ("styles/ideogram4/skill.md", 35000),
    ):
        try:
            _read_skill_file(rel, limit)
        except Exception:
            pass
