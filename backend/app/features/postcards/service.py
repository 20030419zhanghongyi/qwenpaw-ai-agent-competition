"""Build safe postcard captions and rendered SVG assets from completed check-ins."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from html import escape
import logging
import re
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.core.config import settings
from app.db.models import Postcard as PostcardRecord
from app.db.session import SessionLocal
from app.features.pois.repository import PoiRepository
from app.features.review.api import review_text
from app.features.routes.poi_metadata import get_poi_metadata
from app.features.routes.repository import get_template
from app.features.trips.models import Trip
from app.features.trips.repository import trip_repository
from app.guardrails.runtime import record_audit
from app.tools.scrub import scrub

from .models import PostcardResponse
from .repository import PostcardRepository, postcard_repository
from .scene_image import generate_ai_scene

logger = logging.getLogger("macau_storywalk.postcards")

SUPPORTED_LANGUAGES = {"zh-CN", "zh-TW", "en", "pt"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MACAU_TZ = ZoneInfo("Asia/Macau")


class PostcardError(ValueError):
    pass


class PostcardNotFoundError(LookupError):
    pass


def _fallback_caption(poi_name: str, language: str) -> str:
    templates = {
        "zh-CN": f"在{poi_name}，把这一刻留给澳门。",
        "zh-TW": f"在{poi_name}，把這一刻留給澳門。",
        "en": f"A Macau moment, kept at {poi_name}.",
        "pt": f"Um momento de Macau guardado em {poi_name}.",
    }
    return templates.get(language, templates["zh-CN"])


def _clean_agent_caption(text: str) -> str:
    cleaned = " ".join((text or "").replace("\n", " ").split()).strip(" \"'“”")
    return cleaned[:120].rstrip("，,;；")


def _agent_caption(poi_name: str, language: str) -> str | None:
    """Optional guide caption — skipped by default for create latency.

    Postcard create already felt slow when scene+caption both hit QwenPaw.
    Keep template captions unless explicitly enabled later.
    """
    if not settings.guide_agent_enabled:
        return None
    # Caption agent adds another full chat turn; prefer templates for snappy UX.
    if not getattr(settings, "postcard_ai_caption_enabled", False):
        return None
    prompt = (
        f"地点：{poi_name}\n语言：{language}\n"
        "请只输出一句不超过 40 个汉字或 100 个字符的旅行明信片文案。"
        "不得编造历史、日期、人物或事实；不要使用引号、标题、JSON 或 Markdown。"
    )
    try:
        caption = _clean_agent_caption(
            QwenPawClient(timeout=12.0).ask("guide", prompt, session_name="postcard-caption")
        )
        return caption or None
    except QwenPawError as exc:
        logger.info("postcard caption agent unavailable, using template: %s", exc)
        return None


def _caption(poi_name: str, language: str) -> tuple[str, str, str, bool, str]:
    agent_caption = _agent_caption(poi_name, language)
    caption = agent_caption or _fallback_caption(poi_name, language)
    verdict = review_text(caption, source_type="ai" if agent_caption else "template")
    if verdict["decision"] != "pass":
        caption = _fallback_caption(poi_name, language)
        return caption, "template", "template", False, "fallback"
    if agent_caption:
        return caption, "agent", "ai", True, verdict["decision"]
    return caption, "template", "template", False, verdict["decision"]


def _format_timestamp(visited_at: datetime, language: str) -> str:
    local = visited_at.astimezone(MACAU_TZ)
    if language == "pt":
        return local.strftime("%d/%m/%Y %H:%M · Macau")
    if language == "en":
        return local.strftime("%Y-%m-%d %H:%M · Macau")
    return local.strftime("%Y-%m-%d %H:%M · 澳门")


def _format_geo_label(
    *,
    latitude: float | None,
    longitude: float | None,
    district: str | None,
    language: str,
) -> str:
    parts: list[str] = []
    if latitude is not None and longitude is not None:
        # Public POI coordinates, rounded (~100 m) — never photo EXIF.
        lat_hem = "N" if latitude >= 0 else "S"
        lng_hem = "E" if longitude >= 0 else "W"
        parts.append(f"{abs(latitude):.3f}°{lat_hem} {abs(longitude):.3f}°{lng_hem}")
    if district:
        parts.append(district)
    if not parts:
        return "Macau" if language in {"en", "pt"} else "澳门"
    return " · ".join(parts)


def _format_task_label(
    *,
    stop_order: int,
    total_stops: int,
    route_name: str | None,
    language: str,
) -> str:
    stop_n = stop_order + 1
    if language == "zh-TW":
        stop_part = f"第 {stop_n} 站"
        if total_stops > 0:
            stop_part = f"第 {stop_n}/{total_stops} 站"
    elif language == "en":
        stop_part = f"Stop {stop_n}"
        if total_stops > 0:
            stop_part = f"Stop {stop_n} of {total_stops}"
    elif language == "pt":
        stop_part = f"Paragem {stop_n}"
        if total_stops > 0:
            stop_part = f"Paragem {stop_n} de {total_stops}"
    else:
        stop_part = f"第 {stop_n} 站"
        if total_stops > 0:
            stop_part = f"第 {stop_n}/{total_stops} 站"
    if route_name:
        return f"{stop_part} · {route_name}"
    return stop_part


def _placeholder_photo(poi_name: str, language: str) -> bytes:
    """Scenic souvenir illustration when AI scene is unavailable — no EXIF."""
    from io import BytesIO

    from PIL import Image, ImageDraw, ImageFont

    width, height = 960, 720
    image = Image.new("RGB", (width, height), "#7eb6c9")
    draw = ImageDraw.Draw(image)

    # Soft afternoon sky → harbor water (Macau postcard feel).
    for y in range(height):
        t = y / max(height - 1, 1)
        if t < 0.55:
            u = t / 0.55
            r = int(126 + (244 - 126) * u * 0.35)
            g = int(182 + (210 - 182) * u)
            b = int(201 + (180 - 201) * u)
        else:
            u = (t - 0.55) / 0.45
            r = int(62 + (34 - 62) * u)
            g = int(118 + (86 - 118) * u)
            b = int(132 + (110 - 132) * u)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Distant skyline / port terminal silhouette.
    horizon = int(height * 0.58)
    draw.polygon(
        [
            (80, horizon),
            (140, horizon - 90),
            (210, horizon - 70),
            (260, horizon - 140),
            (340, horizon - 100),
            (420, horizon - 160),
            (520, horizon - 90),
            (610, horizon - 130),
            (700, horizon - 70),
            (780, horizon - 110),
            (880, horizon - 60),
            (920, horizon),
        ],
        fill="#2b3937",
    )
    # Modern port hall block.
    draw.rectangle((360, horizon - 120, 620, horizon), fill="#3d4f4c")
    draw.rectangle((380, horizon - 100, 600, horizon - 20), fill="#cfe3e0")
    for x in range(400, 590, 36):
        draw.rectangle((x, horizon - 92, x + 18, horizon - 28), fill="#7aa8a2")

    # Warm paper frame + azulejo accent strip.
    draw.rectangle((28, 28, width - 28, height - 28), outline="#fffaf2", width=10)
    tile_y = height - 78
    for i, x in enumerate(range(48, width - 48, 28)):
        fill = "#2f6f6a" if i % 2 == 0 else "#a5573f"
        draw.rectangle((x, tile_y, x + 24, tile_y + 24), fill=fill)

    font = ImageFont.load_default()
    title = {
        "zh-CN": "澳门印记",
        "zh-TW": "澳門印記",
        "en": "Macau imprint",
        "pt": "Marca de Macau",
    }.get(language, "澳门印记")
    label = (poi_name or "Macau")[:28]
    draw.text((56, 52), title, fill="#fffaf2", font=font)
    draw.text((56, 84), label, fill="#fffaf2", font=font)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def _render_svg(
    *,
    photo_jpeg: bytes | None,
    scene_svg: str | None,
    poi_name: str,
    caption: str,
    timestamp_label: str,
    geo_label: str,
    task_label: str,
    scene_source: str,
) -> bytes:
    """Compose a postcard SVG. Geo comes from public POI data, not photo EXIF.

    Scene provenance lives in a non-visible ``data-scene-source`` attribute and
    in the API/UI badges — not as footer copy inside the souvenir face.
    """
    if scene_svg and scene_source in {"ai", "library"} and not photo_jpeg:
        # Nested illustration from QwenPaw (already sanitized).
        inner = scene_svg.strip()
        if inner.lower().startswith("<svg"):
            # Force placement inside the photo panel.
            inner = re.sub(
                r"<svg\b",
                '<svg x="78" y="78" width="658" height="644" preserveAspectRatio="xMidYMid slice"',
                inner,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            inner = (
                f'<svg x="78" y="78" width="658" height="644" viewBox="0 0 960 720">'
                f"{inner}</svg>"
            )
        photo_layer = inner
    else:
        photo_base64 = base64.b64encode(photo_jpeg or b"").decode("ascii")
        photo_layer = (
            f'<image x="78" y="78" width="658" height="644" '
            f'preserveAspectRatio="xMidYMid slice" '
            f'href="data:image/jpeg;base64,{photo_base64}"/>'
        )
    source_attr = escape(scene_source or "placeholder", quote=True)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800" role="img" aria-label="Postcard from {escape(poi_name)}" data-scene-source="{source_attr}">
  <rect width="1200" height="800" fill="#f4eadb"/>
  <rect x="44" y="44" width="1112" height="712" rx="24" fill="#fffaf2" stroke="#a5573f" stroke-width="6"/>
  {photo_layer}
  <line x1="788" y1="106" x2="788" y2="694" stroke="#d9c0a8" stroke-width="3"/>
  <text x="842" y="150" fill="#a5573f" font-family="Noto Serif CJK SC, Songti SC, serif" font-size="48" font-weight="700">MACAU</text>
  <text x="842" y="198" fill="#806f63" font-family="Arial, sans-serif" font-size="18">{escape(task_label)}</text>
  <text x="842" y="268" fill="#2b3937" font-family="Noto Serif CJK SC, Songti SC, serif" font-size="34">{escape(poi_name)}</text>
  <foreignObject x="842" y="300" width="254" height="200"><div xmlns="http://www.w3.org/1999/xhtml" style="font: 28px 'Noto Serif CJK SC', serif; color:#39413d; line-height:1.45;">{escape(caption)}</div></foreignObject>
  <line x1="842" y1="540" x2="1096" y2="540" stroke="#d9c0a8" stroke-width="2"/>
  <text x="842" y="585" fill="#806f63" font-family="Arial, sans-serif" font-size="20">{escape(timestamp_label)}</text>
  <text x="842" y="640" fill="#806f63" font-family="Arial, sans-serif" font-size="18">{escape(geo_label)}</text>
</svg>'''.encode("utf-8")


def _scene_source_from_record(record: PostcardRecord) -> str:
    if record.photo_scrubbed:
        return "user"
    svg = record.image_svg or b""
    if b'data-scene-source="library"' in svg:
        return "library"
    if b'data-scene-source="ai"' in svg or b"AI scene" in svg:
        return "ai"
    return "placeholder"


class PostcardService:
    def __init__(self, repository: PostcardRepository) -> None:
        self._repository = repository

    def _poi_snapshot(self, poi_id: str) -> tuple[str, float | None, float | None, str | None]:
        """Return poi_name, lat, lng, district. Coordinates are public POI data only."""
        meta = get_poi_metadata(poi_id) or {}
        district = str(meta.get("district") or "") or None
        coords = meta.get("coordinates") or {}
        meta_lat = coords.get("lat")
        meta_lng = coords.get("lng")
        with SessionLocal() as session:
            poi = PoiRepository(session).get_by_id(poi_id)
        if poi is None and not meta:
            raise PostcardError(f"POI not found: {poi_id}")
        name = (poi.poi_name if poi else None) or str(meta.get("name_zh") or poi_id)
        latitude = float(poi.latitude) if poi is not None else None
        longitude = float(poi.longitude) if poi is not None else None
        if latitude is None and isinstance(meta_lat, (int, float)):
            latitude = float(meta_lat)
        if longitude is None and isinstance(meta_lng, (int, float)):
            longitude = float(meta_lng)
        return name, latitude, longitude, district

    def _route_name(self, route_id: str) -> str | None:
        template = get_template(route_id)
        if not template:
            return None
        name = template.get("name")
        return str(name) if name else None

    def _stamps(
        self,
        *,
        trip: Trip,
        poi_id: str,
        stop_order: int,
        language: str,
        visited_at: datetime,
    ) -> dict:
        poi_name, latitude, longitude, district = self._poi_snapshot(poi_id)
        route_name = self._route_name(trip.route_id)
        timestamp_label = _format_timestamp(visited_at, language)
        geo_label = _format_geo_label(
            latitude=latitude,
            longitude=longitude,
            district=district,
            language=language,
        )
        task_label = _format_task_label(
            stop_order=stop_order,
            total_stops=len(trip.stop_poi_ids),
            route_name=route_name,
            language=language,
        )
        return {
            "poi_name": poi_name,
            "visited_at": visited_at,
            "timestamp_label": timestamp_label,
            "geo_label": geo_label,
            "latitude": latitude,
            "longitude": longitude,
            "district": district,
            "route_id": trip.route_id,
            "route_name": route_name,
            "task_label": task_label,
        }

    def _to_response(self, record: PostcardRecord, trip: Trip) -> PostcardResponse:
        stamps = self._stamps(
            trip=trip,
            poi_id=record.poi_id,
            stop_order=record.stop_order,
            language=record.language,
            visited_at=record.created_at,
        )
        # User uploads are always scrubbed; placeholder/AI cards keep photo_scrubbed=False.
        has_user_photo = bool(record.photo_scrubbed)
        scene_source = _scene_source_from_record(record)
        return PostcardResponse(
            postcard_id=record.id,
            trip_id=record.trip_id,
            poi_id=record.poi_id,
            poi_name=stamps["poi_name"],
            stop_order=record.stop_order,
            caption=record.caption,
            caption_source=record.caption_source,
            source_type=record.source_type,
            ai_generated=record.ai_generated,
            language=record.language,
            review_decision=record.review_decision,
            photo_scrubbed=record.photo_scrubbed,
            has_user_photo=has_user_photo,
            scene_source=scene_source,
            image_url=f"/api/v1/postcards/{record.id}/image",
            created_at=record.created_at,
            visited_at=stamps["visited_at"],
            timestamp_label=stamps["timestamp_label"],
            geo_label=stamps["geo_label"],
            latitude=stamps["latitude"],
            longitude=stamps["longitude"],
            district=stamps["district"],
            route_id=stamps["route_id"],
            route_name=stamps["route_name"],
            task_label=stamps["task_label"],
        )

    def create(
        self,
        trip_id: str,
        poi_id: str,
        photo_bytes: bytes | None,
        language: str,
        *,
        replace: bool = False,
        ai_scene: bool = False,
    ) -> PostcardResponse:
        if language not in SUPPORTED_LANGUAGES:
            raise PostcardError("unsupported language")
        raw = photo_bytes or b""
        if len(raw) > MAX_UPLOAD_BYTES:
            raise PostcardError("photo exceeds 8 MiB limit")

        trip = trip_repository.get_trip(trip_id)
        if trip is None:
            raise PostcardNotFoundError(f"Trip not found: {trip_id}")
        if poi_id not in trip.stop_poi_ids:
            raise PostcardError(f"POI is not part of trip {trip_id}: {poi_id}")
        if poi_id not in trip.checked_in_poi_ids:
            raise PostcardError(f"POI must be checked in before postcard generation: {poi_id}")

        existing = self._repository.get_for_trip_poi(trip_id, poi_id)
        if existing is not None:
            if not replace:
                return self._to_response(existing, trip)
            self._repository.delete(existing.id)
            record_audit(
                kind="postcard.delete",
                status="replaced",
                subject=trip_id,
                metadata={"poi_id": poi_id, "postcard_id": existing.id, "reason": "replace"},
            )

        created_at = datetime.now(timezone.utc)
        stop_order = trip.stop_poi_ids.index(poi_id)
        stamps = self._stamps(
            trip=trip,
            poi_id=poi_id,
            stop_order=stop_order,
            language=language,
            visited_at=created_at,
        )
        has_user_photo = bool(raw)
        scene_svg: str | None = None
        if has_user_photo:
            try:
                cleaned_photo = scrub(raw)
            except Exception as exc:  # noqa: BLE001
                raise PostcardError("photo must be a valid image") from exc
            photo_scrubbed = True
            scene_source = "user"
        else:
            _src, ai_photo, ai_svg = generate_ai_scene(
                poi_id=poi_id,
                poi_name=stamps["poi_name"],
                district=stamps.get("district"),
                language=language,
                ai_scene=ai_scene,
                when=created_at,
            )
            if ai_photo or ai_svg:
                cleaned_photo = ai_photo
                scene_svg = ai_svg if not ai_photo else None
                scene_source = _src or "ai"
            else:
                cleaned_photo = _placeholder_photo(stamps["poi_name"], language)
                scene_source = "placeholder"
            photo_scrubbed = False

        caption, caption_source, source_type, ai_generated, review_decision = _caption(
            stamps["poi_name"], language
        )
        record = PostcardRecord(
            id=str(uuid4()),
            trip_id=trip_id,
            poi_id=poi_id,
            stop_order=stop_order,
            caption=caption,
            caption_source=caption_source,
            source_type=source_type,
            ai_generated=ai_generated,
            language=language,
            review_decision=review_decision,
            image_svg=_render_svg(
                photo_jpeg=cleaned_photo,
                scene_svg=scene_svg,
                poi_name=stamps["poi_name"],
                caption=caption,
                timestamp_label=stamps["timestamp_label"],
                geo_label=stamps["geo_label"],
                task_label=stamps["task_label"],
                scene_source=scene_source,
            ),
            photo_scrubbed=photo_scrubbed,
            created_at=created_at,
        )
        saved = self._repository.create(record)
        record_audit(
            kind="postcard.create",
            status="agent" if ai_generated else "template",
            subject=trip_id,
            agent_id="guide" if ai_generated else None,
            decision=review_decision,
            input_chars=len(poi_id) + len(raw),
            output_chars=len(caption),
            metadata={
                "poi_id": poi_id,
                "photo_scrubbed": photo_scrubbed,
                "has_user_photo": has_user_photo,
                "scene_source": scene_source,
                "geo_from_poi": True,
                "task_label": stamps["task_label"],
                "replaced": replace,
                "ai_scene_requested": ai_scene,
            },
        )
        return self._to_response(saved, trip)

    def delete(self, postcard_id: str) -> None:
        record = self._repository.get(postcard_id)
        if record is None:
            raise PostcardNotFoundError(f"Postcard not found: {postcard_id}")
        trip_id = record.trip_id
        poi_id = record.poi_id
        if not self._repository.delete(postcard_id):
            raise PostcardNotFoundError(f"Postcard not found: {postcard_id}")
        record_audit(
            kind="postcard.delete",
            status="ok",
            subject=trip_id,
            metadata={"poi_id": poi_id, "postcard_id": postcard_id},
        )

    def list_by_trip(self, trip_id: str) -> list[PostcardResponse]:
        trip = trip_repository.get_trip(trip_id)
        if trip is None:
            raise PostcardNotFoundError(f"Trip not found: {trip_id}")
        records = self._repository.list_by_trip(trip_id)
        return [self._to_response(record, trip) for record in records]

    def image(self, postcard_id: str) -> bytes:
        record = self._repository.get(postcard_id)
        if record is None:
            raise PostcardNotFoundError(f"Postcard not found: {postcard_id}")
        return record.image_svg


postcard_service = PostcardService(postcard_repository)
