"""Scenic art for postcards when the user skips a personal photo.

Default path is instant local illustration. Optional AI (QwenPaw SVG / wanx)
is opt-in via ``ai_scene=True`` because a full agent draw often takes 1–2 minutes.
Successful AI scenes are cached per POI+language for later regenerations.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path

import httpx

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.core.config import settings

from .scene_library import load_pregenerated_svg

logger = logging.getLogger("macau_storywalk.postcard_scene")

_SVG_BLOCK = re.compile(r"<svg\b[^>]*>.*?</svg>", re.IGNORECASE | re.DOTALL)
_FENCE = re.compile(r"```(?:svg|xml)?\s*([\s\S]*?)```", re.IGNORECASE)
_DANGEROUS_TAGS = re.compile(
    r"<\s*(script|foreignObject|iframe|object|embed)\b[^>]*>.*?<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_DANGEROUS_ATTR = re.compile(r"\son[a-z]+\s*=\s*(['\"]).*?\1|javascript:", re.IGNORECASE)


def build_scene_prompt(
    *,
    poi_name: str,
    district: str | None,
    language: str,
) -> str:
    place = district or ("Macau" if language.startswith("en") or language == "pt" else "澳门")
    return (
        f"Travel postcard illustration of {poi_name} in {place}, Macau, "
        "soft afternoon light, Portuguese-Macanese architecture, azulejo tile accent, "
        "warm paper texture, cinematic composition, no people faces, no text, "
        "no watermark, no logo, tasteful souvenir art"
    )


def _qwenpaw_svg_prompt(*, poi_name: str, district: str | None, language: str) -> str:
    place = district or ("Macau" if language.startswith("en") or language == "pt" else "澳门")
    return (
        f"地点：{poi_name}（{place}，澳门）\n"
        "请画一张旅行明信片插画，只输出完整 SVG 代码，不要 Markdown、不要解释。\n"
        "硬性要求：\n"
        "1) 根元素必须是 <svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 960 720\">；\n"
        "2) 画该地点可辨识的场景（口岸/建筑/水面/街巷等），午后暖光；\n"
        "3) 可用青绿与砖红花砖色点缀，风格像纪念品插画而非写实照片；\n"
        "4) 不要任何文字、人脸、logo、水印；不要 <script> / 事件属性 / foreignObject。\n"
        "5) 尽量简短（元素少、路径简单），便于快速生成。\n"
    )


def _sanitize_svg(raw: str) -> str | None:
    text = (raw or "").strip()
    if not text:
        return None
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    match = _SVG_BLOCK.search(text)
    if match:
        svg = match.group(0)
    else:
        # Model sometimes truncates before </svg>; keep a closable prefix if it looks like SVG.
        start = re.search(r"<svg\b[^>]*>", text, flags=re.IGNORECASE)
        if not start:
            return None
        svg = text[start.start() :].strip()
        if "</svg>" not in svg.lower():
            svg = svg.rstrip() + "\n</svg>"
        if not _SVG_BLOCK.search(svg):
            return None
        svg = _SVG_BLOCK.search(svg).group(0)  # type: ignore[union-attr]
    svg = _DANGEROUS_TAGS.sub("", svg)
    svg = _DANGEROUS_ATTR.sub("", svg)
    if "viewBox" not in svg:
        svg = svg.replace("<svg", '<svg viewBox="0 0 960 720"', 1)
    if len(svg) > 80_000:
        logger.info("postcard AI scene SVG rejected: too large (%s)", len(svg))
        return None
    return svg


def _cache_dir() -> Path:
    path = settings.data_dir / "postcard_scene_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_key(*, poi_name: str, district: str | None, language: str) -> str:
    raw = f"{language}|{district or ''}|{poi_name}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:20]


def _load_cached_svg(*, poi_name: str, district: str | None, language: str) -> str | None:
    path = _cache_dir() / f"{_cache_key(poi_name=poi_name, district=district, language=language)}.svg"
    if not path.is_file():
        return None
    try:
        return _sanitize_svg(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.info("postcard AI scene cache read failed: %s", exc)
        return None


def _store_cached_svg(
    *,
    poi_name: str,
    district: str | None,
    language: str,
    svg: str,
) -> None:
    path = _cache_dir() / f"{_cache_key(poi_name=poi_name, district=district, language=language)}.svg"
    try:
        path.write_text(svg, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.info("postcard AI scene cache write failed: %s", exc)


def _svg_to_jpeg(svg: str) -> bytes | None:
    try:
        import cairosvg  # type: ignore
    except Exception:
        return None
    try:
        png = cairosvg.svg2png(
            bytestring=svg.encode("utf-8"), output_width=960, output_height=720
        )
        from PIL import Image

        image = Image.open(BytesIO(png)).convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=88)
        return buffer.getvalue()
    except Exception as exc:  # noqa: BLE001
        logger.info("postcard AI scene SVG rasterize failed: %s", exc)
        return None


def generate_ai_scene_via_qwenpaw(
    *,
    poi_name: str,
    district: str | None = None,
    language: str = "zh-CN",
) -> tuple[bytes | None, str | None]:
    """Return ``(jpeg, svg)`` from cache or QwenPaw."""
    cached = _load_cached_svg(poi_name=poi_name, district=district, language=language)
    if cached:
        return _svg_to_jpeg(cached), cached

    prompt = _qwenpaw_svg_prompt(poi_name=poi_name, district=district, language=language)
    timeout = max(8.0, float(settings.postcard_ai_scene_timeout or 25.0))
    # One agent only — dual fallback nearly doubles latency.
    agent_id = "default"
    try:
        raw = QwenPawClient(timeout=timeout).ask(
            agent_id,
            prompt,
            session_name="postcard-scene",
        )
    except QwenPawError as exc:
        logger.info("postcard AI scene QwenPaw unavailable: %s", exc)
        return None, None

    svg = _sanitize_svg(raw)
    if not svg:
        logger.info("postcard AI scene QwenPaw(%s) returned no usable SVG", agent_id)
        return None, None
    _store_cached_svg(poi_name=poi_name, district=district, language=language, svg=svg)
    return _svg_to_jpeg(svg), svg


def _wanx_jpeg(
    *,
    poi_name: str,
    district: str | None,
    language: str,
) -> bytes | None:
    api_key = (settings.dashscope_api_key or "").strip()
    if not api_key:
        return None
    try:
        from dashscope import ImageSynthesis
    except Exception as exc:  # noqa: BLE001
        logger.info("postcard AI scene import failed: %s", exc)
        return None

    prompt = build_scene_prompt(poi_name=poi_name, district=district, language=language)
    model = settings.qwen_image_model or ImageSynthesis.Models.wanx_v1
    try:
        response = ImageSynthesis.call(
            model=model,
            prompt=prompt,
            n=1,
            size=settings.postcard_ai_image_size or "1024*1024",
            api_key=api_key,
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("postcard AI scene wanx call failed: %s", exc)
        return None

    status_code = getattr(response, "status_code", None)
    output = getattr(response, "output", None)
    results = getattr(output, "results", None) if output is not None else None
    if not results and isinstance(output, dict):
        results = output.get("results") or []
    if not results:
        logger.info(
            "postcard AI scene wanx empty status=%s code=%s message=%s",
            status_code,
            getattr(response, "code", None),
            str(getattr(response, "message", ""))[:160],
        )
        return None

    first = results[0]
    url = first.get("url") if isinstance(first, dict) else getattr(first, "url", None)
    if not url:
        return None

    try:
        with httpx.Client(timeout=45.0, trust_env=False, follow_redirects=True) as client:
            raw = client.get(url).content
        from PIL import Image

        image = Image.open(BytesIO(raw)).convert("RGB").resize((960, 720))
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=88)
        return buffer.getvalue()
    except Exception as exc:  # noqa: BLE001
        logger.info("postcard AI scene wanx download/decode failed: %s", exc)
        return None


def generate_ai_scene(
    *,
    poi_id: str | None = None,
    poi_name: str,
    district: str | None = None,
    language: str = "zh-CN",
    ai_scene: bool = False,
    when: datetime | None = None,
) -> tuple[str, bytes | None, str | None]:
    """Resolve scene art for a no-photo postcard.

    Order:
    1. Pre-generated library by POI + visit time (instant)
    2. Live QwenPaw / wanx when ``ai_scene=True``
    3. Empty → caller uses local placeholder
    """
    visit = when or datetime.now()
    if poi_id:
        hit = load_pregenerated_svg(poi_id, when=visit)
        if hit:
            _slot, svg = hit
            return "library", _svg_to_jpeg(svg), svg

    if not ai_scene or not settings.postcard_ai_image_enabled:
        return "", None, None

    jpeg, svg = generate_ai_scene_via_qwenpaw(
        poi_name=poi_name, district=district, language=language
    )
    if jpeg or svg:
        return "ai", jpeg, svg

    wanx = _wanx_jpeg(poi_name=poi_name, district=district, language=language)
    if wanx:
        return "ai", wanx, None

    return "", None, None


def generate_ai_scene_jpeg(
    *,
    poi_name: str,
    district: str | None = None,
    language: str = "zh-CN",
) -> bytes | None:
    """Back-compat helper — JPEG only, opt-in AI path."""
    _source, jpeg, _svg = generate_ai_scene(
        poi_name=poi_name,
        district=district,
        language=language,
        ai_scene=True,
    )
    return jpeg
