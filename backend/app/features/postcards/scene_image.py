"""QwenPaw scene generation for postcards without a personal photo."""

from __future__ import annotations

import hashlib
import logging
import threading
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.core.config import settings

logger = logging.getLogger("macau_storywalk.postcard_scene")

DEFAULT_PHOTO_STYLE = "souvenir"
DEFAULT_SCENE_STYLE = "gc-minimal-zine-poster"
SCENE_CACHE_VERSION = "v2"
PHOTO_STYLE_PROMPTS = {
    "souvenir": "雅致澳门旅行纪念品插画，柔和纸张纹理，暖色电影光线",
    "watercolor": "轻盈透明水彩画，细腻纸纹，柔和晕染，保留主体轮廓",
    "azulejo": "葡式蓝白花砖插画，青蓝与砖红点缀，精致平面装饰艺术",
    "vintage": "复古旅行海报，低饱和暖色，胶片颗粒，二十世纪中叶印刷质感",
    "ink": "现代水墨淡彩，留白克制，流畅线条，青绿与赭石点染",
}
SUPPORTED_PHOTO_STYLES = frozenset(PHOTO_STYLE_PROMPTS)
_SCENE_LOCKS: dict[str, threading.Lock] = {}
_SCENE_LOCKS_GUARD = threading.Lock()


class SceneGenerationError(RuntimeError):
    """Raised when the Scene Agent cannot produce a usable postcard image."""


def _scene_lock(key: str) -> threading.Lock:
    with _SCENE_LOCKS_GUARD:
        return _SCENE_LOCKS.setdefault(key, threading.Lock())

def build_scene_prompt(
    *,
    poi_name: str,
    district: str | None,
    language: str,
) -> str:
    place = district or ("Macau" if language.startswith("en") or language == "pt" else "澳门")
    return (
        f"Visual preset: {DEFAULT_SCENE_STYLE}. Create a landscape 4:3 editorial travel-zine "
        f"poster featuring the real, recognizable {poi_name} in {place}, Macau as the sole "
        "subject. Use an asymmetric cut-paper collage, bold flat geometric shapes, simplified "
        "architectural silhouettes, generous negative space, visible halftone and risograph "
        "grain on off-white recycled paper. Palette: deep forest green and black ink with "
        "restrained vermilion and cobalt accents. Keep the landmark geographically and "
        "architecturally specific; do not replace it with a generic Macau skyline, harbour, "
        "or the Ruins of St. Paul's. No card border, UI, people faces, text, letters, numbers, "
        "watermark, or logo. The application adds all typography separately."
    )


def _qwenpaw_image_prompt(*, poi_name: str, district: str | None, language: str) -> str:
    prompt = build_scene_prompt(poi_name=poi_name, district=district, language=language)
    size = settings.postcard_ai_image_size or "2368*1728"
    return (
        "先加载并严格执行 /gc-minimal-zine-poster 技能。你是明信片场景生成 Agent。"
        "必须调用 generate_image_qwen 工具且只调用一次，不要用 SVG、代码、旧场景库、"
        "占位图或文字描述代替图片。\n"
        f"地点：{poi_name}\n行政区：{district or 'Macau'}\n界面语言：{language}\n"
        f"prompt：{prompt}\n"
        f"size：{size}\n"
        "n：1\n"
        "negative_prompt：人物脸部、文字、字母、数字、logo、水印、通用城市天际线、"
        "港口占位图、大三巴占位图、低清晰度、变形建筑。\n"
        "prompt_extend：true。生成成功后只返回工具生成的图片；工具失败时明确返回失败。"
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


def _cache_key(
    *,
    poi_id: str | None,
    poi_name: str,
    district: str | None,
    language: str,
) -> str:
    # Generated scenes contain no text, so a canonical POI can be reused across UI languages.
    identity = poi_id or f"{language}|{district or ''}|{poi_name}"
    raw = f"{DEFAULT_SCENE_STYLE}|{SCENE_CACHE_VERSION}|{identity}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:20]


def _load_cached_jpeg(
    *,
    poi_id: str | None,
    poi_name: str,
    district: str | None,
    language: str,
) -> bytes | None:
    key = _cache_key(
        poi_id=poi_id,
        poi_name=poi_name,
        district=district,
        language=language,
    )
    path = _cache_dir() / f"{key}.jpg"
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
    poi_id: str | None,
    poi_name: str,
    district: str | None,
    language: str,
    jpeg: bytes,
) -> None:
    key = _cache_key(
        poi_id=poi_id,
        poi_name=poi_name,
        district=district,
        language=language,
    )
    path = _cache_dir() / f"{key}.jpg"
    try:
        path.write_bytes(jpeg)
    except Exception as exc:  # noqa: BLE001
        logger.info("postcard AI scene cache write failed: %s", exc)


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
    poi_id: str | None = None,
    poi_name: str,
    district: str | None = None,
    language: str = "zh-CN",
    reuse_cached: bool = True,
) -> tuple[bytes, None]:
    """Return a cached or newly generated Scene Agent image, otherwise raise."""
    key = _cache_key(
        poi_id=poi_id,
        poi_name=poi_name,
        district=district,
        language=language,
    )
    with _scene_lock(key):
        if reuse_cached:
            cached = _load_cached_jpeg(
                poi_id=poi_id,
                poi_name=poi_name,
                district=district,
                language=language,
            )
            if cached:
                return cached, None

        prompt = _qwenpaw_image_prompt(poi_name=poi_name, district=district, language=language)
        timeout = max(30.0, float(settings.postcard_ai_scene_timeout or 210.0))
        agent_id = settings.scene_agent_id or "scene"
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
            logger.warning("postcard AI scene QwenPaw unavailable: %s", exc)
            raise SceneGenerationError("Scene Agent image generation failed") from exc

        jpeg = _image_to_jpeg(raw)
        if not jpeg:
            logger.warning("postcard AI scene QwenPaw(%s) returned no usable image", agent_id)
            raise SceneGenerationError("Scene Agent returned no usable image")
        _store_cached_jpeg(
            poi_id=poi_id,
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
    """Style a scrubbed user photo with the dedicated photo Agent."""
    if style not in SUPPORTED_PHOTO_STYLES or not settings.postcard_ai_image_enabled:
        return None

    timeout = max(30.0, float(settings.postcard_ai_scene_timeout or 210.0))
    agent_id = settings.postcard_photo_agent_id or "scene-photo"
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


def generate_ai_scene(
    *,
    poi_id: str | None = None,
    poi_name: str,
    district: str | None = None,
    language: str = "zh-CN",
    ai_scene: bool = True,
    when: object | None = None,
    reuse_cached: bool = True,
) -> tuple[str, bytes | None, str | None]:
    """Resolve a no-photo scene exclusively through the configured Scene Agent.

    Compatibility arguments remain in the signature, but local scene libraries and
    generic placeholders are intentionally not valid fallbacks.
    """
    del ai_scene, when
    if not settings.postcard_ai_image_enabled:
        raise SceneGenerationError("Scene Agent image generation is disabled")
    jpeg, _ = generate_ai_scene_via_qwenpaw(
        poi_id=poi_id,
        poi_name=poi_name,
        district=district,
        language=language,
        reuse_cached=reuse_cached,
    )
    return "ai", jpeg, None


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
