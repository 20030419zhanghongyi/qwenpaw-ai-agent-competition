"""Optional Qwen-Image artwork for the Taipa story's completed future letter."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from html import escape
import threading
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.models import Postcard as PostcardRecord
from app.features.postcards.repository import PostcardRepository, postcard_repository
from app.features.postcards.scene_image import (
    SceneGenerationError,
    generate_prompt_image_via_qwenpaw,
)
from app.features.trips.repository import trip_repository
from app.guardrails.runtime import record_audit

from .content import load_story, story_nodes
from .models import FutureLetterResponse, StorySession, StorySessionStatus
from .repository import StorySessionRepository, story_session_repository
from .service import (
    StoryContentVersionError,
    StorySessionNotFoundError,
    StorySessionOwnershipError,
)

TAIPA_STORY_ID = "taipa_letters"
TAIPA_ENDING_ID = "send_future_taipa_letter"
FUTURE_LETTER_KIND = "future_letter"
DEFAULT_REFLECTION = "愿未来仍有人记得，氹仔曾经怎样生活。"
MAX_RENDERED_REFLECTION_CHARS = 1800

_LETTER_LOCKS: dict[str, threading.Lock] = {}
_LETTER_LOCKS_GUARD = threading.Lock()


class FutureLetterNotFoundError(LookupError):
    pass


class FutureLetterConflictError(RuntimeError):
    pass


class FutureLetterUnavailableError(RuntimeError):
    pass


def _letter_lock(session_id: str) -> threading.Lock:
    with _LETTER_LOCKS_GUARD:
        return _LETTER_LOCKS.setdefault(session_id, threading.Lock())


def _future_letter_prompt() -> str:
    return (
        "先加载并严格执行 /qwen-image-postcard 技能。你是氹仔故事游未来信的视觉生成 "
        "Agent。必须调用 generate_image_qwen 工具且只调用一次，不要用 SVG、代码、"
        "旧场景库、占位图或文字描述代替图片。\n"
        "prompt：Vertical illustrated story card, a warm editorial still life of five "
        "unaddressed letters gathered on textured cream paper in old Taipa, Macau. "
        "Each letter is distinguished only by a subtle visual motif: sea wind and a "
        "small wave, a bell shadow, a green domestic window, restrained industrial "
        "paper texture, and a quiet street paving pattern. A sixth blank sheet waits "
        "for the future. Refined paper collage, gentle afternoon light, deep forest "
        "green, warm ochre and muted brick red, calm collective-memory mood, generous "
        "blank space for typography added later by the application. The future is an "
        "addressee, not a science-fiction city prediction. No identifiable people or "
        "fabricated historical artifact.\n"
        "size：1536*2688\n"
        "n：1\n"
        "negative_prompt：任何文字、汉字、字母、数字、邮票面值、logo、水印、二维码、"
        "清晰人脸、科幻霓虹、未来天际线、虚构地标、历史档案编号、变形建筑、低清晰度。\n"
        "prompt_extend：true。生成成功后只返回工具生成的图片；工具失败时明确返回失败。"
    )


def _render_future_letter_svg(*, scene_jpeg: bytes, reflection: str) -> tuple[bytes, bool]:
    rendered = reflection
    truncated = len(rendered) > MAX_RENDERED_REFLECTION_CHARS
    if truncated:
        rendered = f"{rendered[: MAX_RENDERED_REFLECTION_CHARS - 1]}…"

    length = len(rendered)
    if length <= 120:
        font_size = 38
    elif length <= 320:
        font_size = 29
    elif length <= 720:
        font_size = 22
    else:
        font_size = 17

    image_data = base64.b64encode(scene_jpeg).decode("ascii")
    safe_reflection = escape(rendered)
    return (
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1600" viewBox="0 0 900 1600" role="img" aria-label="寄给未来氹仔的未来信" data-scene-source="ai" data-artifact-kind="future_letter">
  <defs>
    <linearGradient id="shade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#172d27" stop-opacity="0.08"/>
      <stop offset="1" stop-color="#172d27" stop-opacity="0.64"/>
    </linearGradient>
    <filter id="paper-shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="14" stdDeviation="18" flood-color="#172d27" flood-opacity="0.25"/>
    </filter>
  </defs>
  <rect width="900" height="1600" fill="#e8dcc8"/>
  <image width="900" height="820" preserveAspectRatio="xMidYMid slice" href="data:image/jpeg;base64,{image_data}"/>
  <rect width="900" height="820" fill="url(#shade)"/>
  <text x="70" y="92" fill="#fffaf0" font-family="Noto Serif CJK SC, Songti SC, serif" font-size="24" letter-spacing="5">MACAU STORYWALK · TAIPA</text>
  <text x="70" y="164" fill="#fffaf0" font-family="Noto Serif CJK SC, Songti SC, serif" font-size="52" font-weight="700">寄给未来氹仔</text>
  <text x="70" y="212" fill="#fffaf0" font-family="Noto Sans CJK SC, sans-serif" font-size="22">未来信与写信关系均为剧情虚构</text>
  <rect x="50" y="540" width="800" height="1000" rx="30" fill="#fffaf0" stroke="#b87652" stroke-width="3" filter="url(#paper-shadow)"/>
  <text x="100" y="628" fill="#8b4c36" font-family="Noto Serif CJK SC, Songti SC, serif" font-size="24" letter-spacing="3">收件人</text>
  <text x="100" y="680" fill="#243f36" font-family="Noto Serif CJK SC, Songti SC, serif" font-size="32" font-weight="700">未来仍愿意记得氹仔如何生活的人</text>
  <line x1="100" y1="722" x2="800" y2="722" stroke="#d8c4a8" stroke-width="2"/>
  <g fill="#365d50" font-family="Noto Sans CJK SC, sans-serif" font-size="22">
    <text x="100" y="778">海信</text><text x="224" y="778">钟信</text>
    <text x="348" y="778">家信</text><text x="472" y="778">工信</text>
    <text x="596" y="778">街信</text>
  </g>
  <foreignObject x="100" y="830" width="700" height="540">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font:{font_size}px 'Noto Serif CJK SC','Songti SC',serif;color:#273a34;line-height:1.68;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;overflow:hidden;">{safe_reflection}</div>
  </foreignObject>
  <line x1="100" y1="1402" x2="800" y2="1402" stroke="#d8c4a8" stroke-width="2"/>
  <text x="100" y="1456" fill="#76685b" font-family="Noto Sans CJK SC, sans-serif" font-size="20">海信、钟信、家信、工信与街信，在这里写向未来。</text>
  <text x="100" y="1496" fill="#8b4c36" font-family="Noto Sans CJK SC, sans-serif" font-size="18">AI 场景示意 · 信中文字为玩家个人创作</text>
</svg>'''.encode("utf-8"),
        truncated,
    )


class FutureLetterService:
    def __init__(
        self,
        sessions: StorySessionRepository,
        postcards: PostcardRepository,
    ) -> None:
        self._sessions = sessions
        self._postcards = postcards

    def _session(self, session_id: str, user_id: str) -> StorySession:
        story_session = self._sessions.get(session_id)
        if story_session is None:
            raise StorySessionNotFoundError(f"Story session not found: {session_id}")
        if story_session.user_id != user_id:
            raise StorySessionOwnershipError("无权访问该故事会话")
        story = load_story(story_session.story_id)
        if story_session.state.content_version != story["version"]:
            raise StoryContentVersionError("该会话属于旧版故事内容，请从故事封面开始新会话")
        return story_session

    @staticmethod
    def _ending_poi_id(story_session: StorySession) -> str:
        if story_session.story_id != TAIPA_STORY_ID:
            raise FutureLetterConflictError("只有氹仔《海风寄来的信》支持生成未来信")
        if (
            story_session.status != StorySessionStatus.COMPLETED
            or story_session.state.ending_id != TAIPA_ENDING_ID
        ):
            raise FutureLetterConflictError("请先完成氹仔故事并保存未来寄语")
        story = load_story(story_session.story_id)
        ending = next((node for node in story_nodes(story) if node["kind"] == "ending"), None)
        poi_id = str((ending or {}).get("poi_id") or "")
        if not poi_id:
            raise FutureLetterConflictError("氹仔终章缺少可用地点")
        return poi_id

    def _record(self, story_session: StorySession, poi_id: str) -> PostcardRecord | None:
        return self._postcards.get_for_trip_poi(
            story_session.trip_id,
            poi_id,
            artifact_kind=FUTURE_LETTER_KIND,
        )

    @staticmethod
    def _response(
        story_session: StorySession,
        record: PostcardRecord,
    ) -> FutureLetterResponse:
        return FutureLetterResponse(
            story_session_id=story_session.session_id,
            postcard_id=record.id,
            image_url=(
                f"/api/v1/story-sessions/{story_session.session_id}/future-letter/image"
            ),
            generated_at=record.created_at,
            reflection_truncated=b'data-reflection-truncated="true"' in record.image_svg,
        )

    def get(self, session_id: str, user_id: str) -> FutureLetterResponse:
        story_session = self._session(session_id, user_id)
        poi_id = self._ending_poi_id(story_session)
        record = self._record(story_session, poi_id)
        if record is None:
            raise FutureLetterNotFoundError("未来信配图尚未生成")
        return self._response(story_session, record)

    def generate(self, session_id: str, user_id: str) -> FutureLetterResponse:
        story_session = self._session(session_id, user_id)
        poi_id = self._ending_poi_id(story_session)
        existing = self._record(story_session, poi_id)
        if existing is not None:
            return self._response(story_session, existing)

        with _letter_lock(session_id):
            existing = self._record(story_session, poi_id)
            if existing is not None:
                return self._response(story_session, existing)
            if not settings.postcard_ai_image_enabled:
                raise FutureLetterUnavailableError("未来信配图功能暂时未启用")

            trip = trip_repository.get_trip(story_session.trip_id)
            if trip is None:
                raise FutureLetterConflictError("故事关联行程不存在")
            if poi_id not in trip.stop_poi_ids or poi_id not in trip.checked_in_poi_ids:
                raise FutureLetterConflictError("请先确认到达氹仔终章地点")

            reflection = (story_session.state.ending_reflection or "").strip()
            caption = reflection or DEFAULT_REFLECTION
            try:
                scene_jpeg = generate_prompt_image_via_qwenpaw(
                    prompt=_future_letter_prompt(),
                    session_prefix=f"taipa-future-letter-{session_id}",
                    output_size=(900, 1600),
                )
                image_svg, truncated = _render_future_letter_svg(
                    scene_jpeg=scene_jpeg,
                    reflection=caption,
                )
                if truncated:
                    image_svg = image_svg.replace(
                        b'data-artifact-kind="future_letter"',
                        b'data-artifact-kind="future_letter" data-reflection-truncated="true"',
                        1,
                    )
            except SceneGenerationError as exc:
                record_audit(
                    kind="story.future_letter.generate",
                    status="failed",
                    subject=session_id,
                    agent_id=settings.scene_agent_id or "scene",
                    metadata={"story_id": TAIPA_STORY_ID, "poi_id": poi_id},
                )
                raise FutureLetterUnavailableError(
                    "海风暂时没能送回配图；文字未来信已经安全保存"
                ) from exc

            created_at = datetime.now(timezone.utc)
            record = PostcardRecord(
                id=str(uuid4()),
                trip_id=story_session.trip_id,
                poi_id=poi_id,
                artifact_kind=FUTURE_LETTER_KIND,
                stop_order=trip.stop_poi_ids.index(poi_id),
                caption=caption,
                caption_source="user" if reflection else "story",
                source_type="story_future_letter",
                ai_generated=False,
                language="zh-CN",
                review_decision="not_required",
                image_svg=image_svg,
                photo_scrubbed=False,
                created_at=created_at,
            )
            try:
                saved = self._postcards.create(record)
            except IntegrityError:
                saved = self._record(story_session, poi_id)
                if saved is None:
                    raise

            record_audit(
                kind="story.future_letter.generate",
                status="ok",
                subject=session_id,
                agent_id=settings.scene_agent_id or "scene",
                input_chars=0,
                output_chars=len(image_svg),
                metadata={
                    "story_id": TAIPA_STORY_ID,
                    "poi_id": poi_id,
                    "postcard_id": saved.id,
                    "reflection_chars": len(caption),
                    "reflection_sent_to_agent": False,
                    "scene_source": "ai",
                },
            )
            return self._response(story_session, saved)

    def image(self, session_id: str, user_id: str) -> bytes:
        story_session = self._session(session_id, user_id)
        poi_id = self._ending_poi_id(story_session)
        record = self._record(story_session, poi_id)
        if record is None:
            raise FutureLetterNotFoundError("未来信配图尚未生成")
        return record.image_svg


future_letter_service = FutureLetterService(story_session_repository, postcard_repository)
