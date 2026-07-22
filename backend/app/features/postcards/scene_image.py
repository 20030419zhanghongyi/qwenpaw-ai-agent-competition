"""Scenic art for postcards when the user skips a personal photo.

Default path is instant local illustration. Optional QwenPaw/Qwen-Image art is
opt-in via ``ai_scene=True`` because generation often takes 1–3 minutes.
Successful AI scenes are cached per POI+language for later regenerations.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import httpx

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.core.config import settings

from .scene_library import load_pregenerated_svg

logger = logging.getLogger("macau_storywalk.postcard_scene")

DEFAULT_PHOTO_STYLE = "souvenir"
PHOTO_STYLE_PROMPTS = {
    "souvenir": "雅致澳门旅行纪念品插画，柔和纸张纹理，暖色电影光线",
    "watercolor": "轻盈透明水彩画，细腻纸纹，柔和晕染，保留主体轮廓",
    "azulejo": "葡式蓝白花砖插画，青蓝与砖红点缀，精致平面装饰艺术",
    "vintage": "复古旅行海报，低饱和暖色，胶片颗粒，二十世纪中叶印刷质感",
    "ink": "现代水墨淡彩，留白克制，流畅线条，青绿与赭石点染",
}
SUPPORTED_PHOTO_STYLES = frozenset(PHOTO_STYLE_PROMPTS)

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


def _qwenpaw_image_prompt(*, poi_name: str, district: str | None, language: str) -> str:
    prompt = build_scene_prompt(poi_name=poi_name, district=district, language=language)
    size = settings.postcard_ai_image_size or "2368*1728"
    return (
        "你是明信片场景生成 Agent。必须调用 generate_image_qwen 工具且只调用一次，"
        "不要用 SVG、代码或文字描述代替图片。\n"
        f"prompt：{prompt}\n"
        f"size：{size}\n"
        "n：1\n"
        "negative_prompt：人物脸部、文字、logo、水印、低清晰度、变形建筑。\n"
        "prompt_extend：true。生成成功后无需解释。"
    )


def _qwenpaw_edit_prompt(
    *,
    reference_path: str,
    style: str,
    poi_name: str,
) -> str:
    style_prompt = PHOTO_STYLE_PROMPTS[style]
    return (
        "你是明信片照片风格化 Agent。必须调用 edit_image_qwen 工具且只调用一次，"
        "不要用代码或文字描述代替图片。\n"
        f"reference_images：仅使用 [{reference_path!r}]。\n"
        f"prompt：把图一转换为{style_prompt}，适合作为 {poi_name} 的旅行明信片主图。"
        "保持原始构图、人物姿态、建筑和物体关系；不得新增人物。"
        "所有已模糊人脸必须继续保持模糊和不可识别，不得补全或重建人脸细节。\n"
        "size：留空以沿用参考图比例。n：1。prompt_extend：true。\n"
        "negative_prompt：清晰人脸、人脸重建、身份特征、文字、logo、水印、"
        "额外人物、变形肢体、变形建筑。生成成功后无需解释。"
    )


def _cache_dir() -> Path:
    path = settings.data_dir / "postcard_scene_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_key(*, poi_name: str, district: str | None, language: str) -> str:
    raw = f"{language}|{district or ''}|{poi_name}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:20]


def _load_cached_jpeg(*, poi_name: str, district: str | None, language: str) -> bytes | None:
    path = _cache_dir() / f"{_cache_key(poi_name=poi_name, district=district, language=language)}.jpg"
    if not path.is_file():
        return None
    try:
        raw = path.read_bytes()
        from PIL import Image

        Image.open(BytesIO(raw)).verify()
        return raw
    except Exception as exc:  # noqa: BLE001
        logger.info("postcard AI scene cache read failed: %s", exc)
        return None


def _store_cached_jpeg(
    *,
    poi_name: str,
    district: str | None,
    language: str,
    jpeg: bytes,
) -> None:
    path = _cache_dir() / f"{_cache_key(poi_name=poi_name, district=district, language=language)}.jpg"
    try:
        path.write_bytes(jpeg)
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


def _image_to_jpeg(raw: bytes) -> bytes | None:
    """Validate generated image bytes and normalize them to a 4:3 JPEG."""
    try:
        from PIL import Image, ImageOps

        image = Image.open(BytesIO(raw)).convert("RGB")
        image = ImageOps.fit(image, (960, 720), method=Image.Resampling.LANCZOS)
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=90, optimize=True)
        return buffer.getvalue()
    except Exception as exc:  # noqa: BLE001
        logger.info("postcard AI scene image decode failed: %s", exc)
        return None


def generate_ai_scene_via_qwenpaw(
    *,
    poi_name: str,
    district: str | None = None,
    language: str = "zh-CN",
) -> tuple[bytes | None, str | None]:
    """Return ``(jpeg, None)`` from cache or the scene Agent image tool."""
    cached = _load_cached_jpeg(poi_name=poi_name, district=district, language=language)
    if cached:
        return cached, None

    prompt = _qwenpaw_image_prompt(poi_name=poi_name, district=district, language=language)
    timeout = max(30.0, float(settings.postcard_ai_scene_timeout or 210.0))
    agent_id = settings.scene_agent_id or "scene"
    key = _cache_key(poi_name=poi_name, district=district, language=language)
    session_id = f"postcard-scene-{key}-{uuid4().hex[:8]}"
    client = QwenPawClient(timeout=timeout)
    try:
        reference = client.ask_for_image(
            agent_id,
            prompt,
            session_id=session_id,
        )
        raw = client.download_media(reference)
    except QwenPawError as exc:
        logger.info("postcard AI scene QwenPaw unavailable: %s", exc)
        return None, None

    jpeg = _image_to_jpeg(raw)
    if not jpeg:
        logger.info("postcard AI scene QwenPaw(%s) returned no usable image", agent_id)
        return None, None
    _store_cached_jpeg(
        poi_name=poi_name,
        district=district,
        language=language,
        jpeg=jpeg,
    )
    return jpeg, None


def stylize_photo_via_qwenpaw(
    *,
    photo_jpeg: bytes,
    style: str = DEFAULT_PHOTO_STYLE,
    poi_name: str,
) -> bytes | None:
    """Style a scrubbed user photo with the scene Agent's edit-image tool."""
    if style not in SUPPORTED_PHOTO_STYLES or not settings.postcard_ai_image_enabled:
        return None

    timeout = max(30.0, float(settings.postcard_ai_scene_timeout or 210.0))
    agent_id = settings.scene_agent_id or "scene"
    session_id = f"postcard-edit-{uuid4().hex}"
    client = QwenPawClient(timeout=timeout)
    try:
        source_path = client.upload_media(
            photo_jpeg,
            filename=f"{session_id}.jpg",
            agent_id=agent_id,
        )
        prompt = _qwenpaw_edit_prompt(
            reference_path=source_path,
            style=style,
            poi_name=poi_name,
        )
        reference = client.ask_for_image(
            agent_id,
            prompt,
            session_id=session_id,
        )
        raw = client.download_media(reference)
    except QwenPawError as exc:
        logger.info("postcard AI photo style unavailable: %s", exc)
        return None
    return _image_to_jpeg(raw)


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
    1. Live QwenPaw Qwen-Image / wanx fallback when ``ai_scene=True``
    2. Pre-generated library by POI + visit time (instant)
    3. Empty → caller uses local placeholder
    """
    visit = when or datetime.now()
    if ai_scene and settings.postcard_ai_image_enabled:
        jpeg, svg = generate_ai_scene_via_qwenpaw(
            poi_name=poi_name, district=district, language=language
        )
        if jpeg or svg:
            return "ai", jpeg, svg

        wanx = _wanx_jpeg(poi_name=poi_name, district=district, language=language)
        if wanx:
            return "ai", wanx, None

    if poi_id:
        hit = load_pregenerated_svg(poi_id, when=visit)
        if hit:
            _slot, svg = hit
            return "library", _svg_to_jpeg(svg), svg

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
