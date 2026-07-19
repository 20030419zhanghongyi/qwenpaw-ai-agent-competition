"""Build safe postcard captions and rendered SVG assets from completed check-ins."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from html import escape
import logging
from uuid import uuid4

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.core.config import settings
from app.db.models import Postcard as PostcardRecord
from app.db.session import SessionLocal
from app.features.pois.repository import PoiRepository
from app.features.review.api import review_text
from app.features.trips.repository import trip_repository
from app.guardrails.runtime import record_audit
from app.tools.scrub import scrub

from .models import PostcardResponse
from .repository import PostcardRepository, postcard_repository

logger = logging.getLogger("macau_storywalk.postcards")

SUPPORTED_LANGUAGES = {"zh-CN", "zh-TW", "en", "pt"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


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
    """Use the existing guide agent when available; a deterministic caption remains safe fallback."""
    if not settings.guide_agent_enabled:
        return None
    prompt = (
        f"地点：{poi_name}\n语言：{language}\n"
        "请只输出一句不超过 40 个汉字或 100 个字符的旅行明信片文案。"
        "不得编造历史、日期、人物或事实；不要使用引号、标题、JSON 或 Markdown。"
    )
    try:
        caption = _clean_agent_caption(
            QwenPawClient().ask("guide", prompt, session_name="postcard-caption")
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


def _render_svg(
    *, photo_jpeg: bytes, poi_name: str, caption: str, created_at: datetime, language: str
) -> bytes:
    """Compose a browser-native postcard asset without storing raw photo metadata or coordinates."""
    photo_base64 = base64.b64encode(photo_jpeg).decode("ascii")
    date_label = created_at.astimezone(timezone.utc).strftime("%Y-%m-%d · Macau")
    if language == "pt":
        date_label = created_at.astimezone(timezone.utc).strftime("%d/%m/%Y · Macau")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800" role="img" aria-label="Postcard from {escape(poi_name)}">
  <rect width="1200" height="800" fill="#f4eadb"/>
  <rect x="44" y="44" width="1112" height="712" rx="24" fill="#fffaf2" stroke="#a5573f" stroke-width="6"/>
  <image x="78" y="78" width="658" height="644" preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{photo_base64}"/>
  <line x1="788" y1="106" x2="788" y2="694" stroke="#d9c0a8" stroke-width="3"/>
  <text x="842" y="165" fill="#a5573f" font-family="Noto Serif CJK SC, Songti SC, serif" font-size="56" font-weight="700">MACAU</text>
  <text x="842" y="250" fill="#2b3937" font-family="Noto Serif CJK SC, Songti SC, serif" font-size="38">{escape(poi_name)}</text>
  <foreignObject x="842" y="292" width="254" height="230"><div xmlns="http://www.w3.org/1999/xhtml" style="font: 30px 'Noto Serif CJK SC', serif; color:#39413d; line-height:1.45;">{escape(caption)}</div></foreignObject>
  <line x1="842" y1="590" x2="1096" y2="590" stroke="#d9c0a8" stroke-width="2"/>
  <text x="842" y="640" fill="#806f63" font-family="Arial, sans-serif" font-size="24">{escape(date_label)}</text>
  <text x="842" y="682" fill="#806f63" font-family="Arial, sans-serif" font-size="20">AI-assisted postcard · photo scrubbed</text>
</svg>'''.encode("utf-8")


class PostcardService:
    def __init__(self, repository: PostcardRepository) -> None:
        self._repository = repository

    @staticmethod
    def _to_response(record: PostcardRecord, poi_name: str) -> PostcardResponse:
        return PostcardResponse(
            postcard_id=record.id,
            trip_id=record.trip_id,
            poi_id=record.poi_id,
            poi_name=poi_name,
            stop_order=record.stop_order,
            caption=record.caption,
            caption_source=record.caption_source,
            source_type=record.source_type,
            ai_generated=record.ai_generated,
            language=record.language,
            review_decision=record.review_decision,
            photo_scrubbed=record.photo_scrubbed,
            image_url=f"/api/v1/postcards/{record.id}/image",
            created_at=record.created_at,
        )

    def _poi_name(self, poi_id: str) -> str:
        with SessionLocal() as session:
            poi = PoiRepository(session).get_by_id(poi_id)
        if poi is None:
            raise PostcardError(f"POI not found: {poi_id}")
        return poi.poi_name

    def create(self, trip_id: str, poi_id: str, photo_bytes: bytes, language: str) -> PostcardResponse:
        if language not in SUPPORTED_LANGUAGES:
            raise PostcardError("unsupported language")
        if not photo_bytes:
            raise PostcardError("photo must not be empty")
        if len(photo_bytes) > MAX_UPLOAD_BYTES:
            raise PostcardError("photo exceeds 8 MiB limit")

        trip = trip_repository.get_trip(trip_id)
        if trip is None:
            raise PostcardNotFoundError(f"Trip not found: {trip_id}")
        if poi_id not in trip.stop_poi_ids:
            raise PostcardError(f"POI is not part of trip {trip_id}: {poi_id}")
        if poi_id not in trip.checked_in_poi_ids:
            raise PostcardError(f"POI must be checked in before postcard generation: {poi_id}")

        existing = self._repository.get_for_trip_poi(trip_id, poi_id)
        poi_name = self._poi_name(poi_id)
        if existing is not None:
            return self._to_response(existing, poi_name)

        try:
            cleaned_photo = scrub(photo_bytes)
        except Exception as exc:  # noqa: BLE001 - invalid uploads must not become server errors
            raise PostcardError("photo must be a valid image") from exc

        created_at = datetime.now(timezone.utc)
        caption, caption_source, source_type, ai_generated, review_decision = _caption(
            poi_name, language
        )
        record = PostcardRecord(
            id=str(uuid4()),
            trip_id=trip_id,
            poi_id=poi_id,
            stop_order=trip.stop_poi_ids.index(poi_id),
            caption=caption,
            caption_source=caption_source,
            source_type=source_type,
            ai_generated=ai_generated,
            language=language,
            review_decision=review_decision,
            image_svg=_render_svg(
                photo_jpeg=cleaned_photo,
                poi_name=poi_name,
                caption=caption,
                created_at=created_at,
                language=language,
            ),
            photo_scrubbed=True,
            created_at=created_at,
        )
        saved = self._repository.create(record)
        record_audit(
            kind="postcard.create",
            status="agent" if ai_generated else "template",
            subject=trip_id,
            agent_id="guide" if ai_generated else None,
            decision=review_decision,
            input_chars=len(poi_id) + len(photo_bytes),
            output_chars=len(caption),
            metadata={"poi_id": poi_id, "photo_scrubbed": True},
        )
        return self._to_response(saved, poi_name)

    def list_by_trip(self, trip_id: str) -> list[PostcardResponse]:
        trip = trip_repository.get_trip(trip_id)
        if trip is None:
            raise PostcardNotFoundError(f"Trip not found: {trip_id}")
        records = self._repository.list_by_trip(trip_id)
        names = {poi_id: self._poi_name(poi_id) for poi_id in {record.poi_id for record in records}}
        return [self._to_response(record, names[record.poi_id]) for record in records]

    def image(self, postcard_id: str) -> bytes:
        record = self._repository.get(postcard_id)
        if record is None:
            raise PostcardNotFoundError(f"Postcard not found: {postcard_id}")
        return record.image_svg


postcard_service = PostcardService(postcard_repository)
