"""拍照识别 / 文化讲解接口（Phase 4 + P2，QwenPaw ``photo`` / ``guide`` agent 驱动）。

- ``POST /api/v1/guide/photo``：上传图 → scrub 脱敏 → photo agent 看图识别 → guide agent 讲解
  （识别恒走 photo agent；讲解走 guide agent + RAG，guide 未启用则 ``explanation`` 留空）。
- ``POST /api/v1/guide/generate``：POI 名/id + 偏好 → RAG 取料 → guide agent 讲解。
- ``POST /api/v1/guide/trigger``：位置 → 最近 POI 提示（用户确认后才生成讲解）。

讲解素材策略（``_gather_material``）：candidate_poi 已点名 → ``get_poi_material`` 精确取整 POI
（最稳，不靠向量）；否则 ``retrieve()`` 向量找相关 POI 兜底。

失败纪律（对齐 routes/intent）：开关关 → 503；agent 抖动 / 解析失败 → 不抛穿，
返回空结果 + ``error`` 字段，仍 200。
"""

from __future__ import annotations

import logging
import os
import tempfile
import time
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.agents import guide_agent, photo_agent
from app.core.config import settings
from app.db.session import get_db
from app.features.pois.models import NearbyPoiResponse
from app.features.pois.service import PoiService
from app.features.review.api import review_text
from app.guardrails.runtime import rate_limit, record_audit, sanitize_untrusted_text
from app.observability.trace import record_trace
from app.tools.scrub import scrub

from .trigger_state import trigger_state
from .tts import TTSUnavailableError, VOICE_BY_LANGUAGE, synthesize_to_oss

# rag/ 在仓库根（不在 backend/app 内）；config.py 导入时已把仓库根加进 sys.path
from rag.retrieve import get_poi_material, retrieve

logger = logging.getLogger("macau_storywalk.guide")

router = APIRouter(prefix="/api/v1/guide", tags=["guide"])

_ALLOW_MIME = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 8 * 1024 * 1024  # 8MB

# block 裁定下，讲解正文替换为这句安全 fallback（原始不安全文本不外泄）
_BLOCK_FALLBACK = "（该讲解未通过安全审核，已暂缓展示，请稍后重试。）"
_LOW_CONFIDENCE_THRESHOLD = 0.6


def _review_guide_text(text: str) -> dict:
    """guide 生成文本 → reviewer 上线前把关（guide→reviewer 管道）。

    返回裁定 dict（含 ``decision``/``source``/``issues``/``reviewer_notes``）。
    reviewer 不可用或任何异常 → ``source="skipped"``，**绝不阻断 guide 主流程**。
    """
    if not (text or "").strip():
        return {"decision": "skip", "source": "skipped", "issues": [], "reviewer_notes": "空文本，跳过审核"}
    try:
        return review_text(text, source_type="ai")
    except Exception as exc:  # noqa: BLE001 - 审核永不阻断 guide
        logger.info("reviewer 把关异常，跳过：%s", exc)
        return {"decision": "skip", "source": "skipped", "issues": [], "reviewer_notes": f"审核跳过：{exc}"}


def _apply_review(text: str, *, path: str) -> tuple[str, dict]:
    """对一段 guide 文本过审：返回 (对外文本, 裁定)。block → 对外文本换成安全 fallback，
    落 guide.review trace。pass/revise → 原文照发。"""
    review = _review_guide_text(text)
    out = _BLOCK_FALLBACK if review.get("decision") == "block" else text
    record_trace(
        kind="guide.review",
        status=review.get("source"),
        agent_id="reviewer" if review.get("source") == "agent" else None,
        input_summary=f"{path}:{len(text or '')}chars decision={review.get('decision')}",
        extra={"decision": review.get("decision"), "path": path},
    )
    return out, review


def _gather_material(candidate_poi: str | None, description: str) -> tuple[str, str]:
    """讲解素材：优先精确取 candidate_poi 整 POI 资料；否则向量检索 description 找相关 POI。

    返回 (poi_name, material)。两者都空时返回 ("", "")，调用方据此跳过讲解。
    """
    if candidate_poi:
        got = get_poi_material(candidate_poi)
        if got and got[1]:
            return got
    if description:
        chunks = retrieve(description, k=4)
        if chunks:
            material = "\n\n".join(
                f"相关资料 {i + 1}（{c['name']}）:\n{c['text']}" for i, c in enumerate(chunks)
            )
            return ("", material)
    return ("", "")


def _explain(
    description: str, candidate_poi: str | None, *, language: str, interests: list[str] | None = None
) -> dict | None:
    """拍照路径的讲解 seam：guide agent + RAG。guide 未启用 / 失败 → 返回 None。"""
    if not settings.guide_agent_enabled:
        return None
    poi_name, material = _gather_material(candidate_poi, description)
    if not material:
        return None
    expl = guide_agent.generate(poi_name, material=material, language=language, interests=interests)
    if expl is None:
        return None
    return {
        "text": expl.text,
        "source_type": expl.source_type,
        "confidence": expl.confidence,
        "ai_generated": expl.ai_generated,
        "language": expl.language,
    }


class GuideRequest(BaseModel):
    poi: str = Field(min_length=1, max_length=255)  # POI 名字（中/英/葡）或 id
    language: str = "zh-CN"
    interests: list[str] | None = None   # history / architecture / food / photo / culture

    @field_validator("poi")
    @classmethod
    def sanitize_poi(cls, value: str) -> str:
        value = sanitize_untrusted_text(value, max_length=255)
        if not value:
            raise ValueError("poi must not be blank")
        return value


class GuideTriggerRequest(BaseModel):
    """Anonymous location check used before the user opts into a narration."""

    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    session_id: str = Field(min_length=1, max_length=128)
    radius_m: float = Field(default=80, ge=10, le=500)
    language: str = "zh-CN"

    @field_validator("session_id")
    @classmethod
    def session_id_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("session_id must not be blank")
        return value


class GuideTriggerResponse(BaseModel):
    triggered: bool
    reason: str | None = None
    poi: NearbyPoiResponse | None = None
    distance_m: float | None = Field(default=None, ge=0)
    prompt: str | None = None
    guide_request: GuideRequest | None = None


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    language: str = "zh-CN"

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        value = sanitize_untrusted_text(value, max_length=20_000)
        if not value:
            raise ValueError("text must not be blank")
        return value

    @field_validator("language")
    @classmethod
    def require_supported_language(cls, value: str) -> str:
        if value not in VOICE_BY_LANGUAGE:
            raise ValueError("unsupported TTS language")
        return value


class TTSResponse(BaseModel):
    audio_url: str
    expires_in: int
    content_type: str
    language: str
    voice: str


@router.post(
    "/trigger",
    response_model=GuideTriggerResponse,
    summary="Detect a nearby POI before generating a guide narration",
)
def trigger(
    req: GuideTriggerRequest,
    database: Annotated[Session, Depends(get_db)],
) -> GuideTriggerResponse:
    """Return one nearby POI prompt without calling the guide agent.

    The client should show the prompt and call ``/guide/generate`` only after
    the user confirms. The session identifier is only used in process memory
    for the ten-minute duplicate-prompt cooldown and is never traced or stored.
    """
    nearby = PoiService(database).nearby(
        longitude=req.longitude,
        latitude=req.latitude,
        radius_m=req.radius_m,
        limit=1,
    )
    if not nearby:
        record_trace(
            kind="guide.trigger",
            status="no_nearby_poi",
            extra={"radius_m": req.radius_m, "triggered": False},
        )
        return GuideTriggerResponse(triggered=False, reason="no_nearby_poi")

    poi = nearby[0]
    allowed = trigger_state.allow_prompt(session_id=req.session_id, poi_id=poi.poi_id)
    if not allowed:
        record_trace(
            kind="guide.trigger",
            status="recently_triggered",
            extra={
                "poi_id": poi.poi_id,
                "distance_m": poi.distance_m,
                "radius_m": req.radius_m,
                "triggered": False,
            },
        )
        return GuideTriggerResponse(
            triggered=False,
            reason="recently_triggered",
            poi=poi,
            distance_m=poi.distance_m,
        )

    prompt = f"你已靠近{poi.poi_name}，要听讲解吗？"
    record_trace(
        kind="guide.trigger",
        status="prompted",
        extra={
            "poi_id": poi.poi_id,
            "distance_m": poi.distance_m,
            "radius_m": req.radius_m,
            "triggered": True,
        },
    )
    return GuideTriggerResponse(
        triggered=True,
        poi=poi,
        distance_m=poi.distance_m,
        prompt=prompt,
        guide_request=GuideRequest(poi=poi.poi_name, language=req.language),
    )


@router.post("/photo", dependencies=[Depends(rate_limit("expensive"))])
async def photo(
    file: UploadFile = File(..., description="用户在澳门街头拍的照片（jpeg/png/webp，≤8MB）"),
    language: str = Query("zh-CN", description="描述/讲解语言：zh-CN/zh-TW/en/pt"),
) -> dict:
    """拍照 → 这是啥 + 讲解（photo agent 看图；guide agent 讲解，未启用则 explanation=null）。"""
    if not settings.photo_agent_enabled:
        raise HTTPException(
            status_code=503,
            detail="photo recognition disabled (need photo agent in QwenPaw + PHOTO_AGENT_ENABLED=true)",
        )
    if file.content_type not in _ALLOW_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported content type: {file.content_type} (allowed: {sorted(_ALLOW_MIME)})",
        )

    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"image too large (>{_MAX_BYTES // 1024 // 1024}MB)")

    scrubbed = scrub(raw)  # EXIF 剥离 + 人脸模糊（恒成功，不抛）

    # 脱敏后的图写到临时文件，交给 QwenPaw photo agent 的 view_image 工具读取
    recog = None
    latency_ms: int | None = None
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    try:
        tmp.write(scrubbed)
        tmp.close()
        t0 = time.perf_counter()
        recog = photo_agent.recognize(tmp.name, language=language)
        latency_ms = int((time.perf_counter() - t0) * 1000)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    if recog is not None:
        status, source = "ok", "agent"
        description, candidate_poi, confidence, error = (
            recog.description,
            recog.candidate_poi,
            recog.confidence,
            None,
        )
    else:
        logger.info("photo agent 不可用或解析失败（可能模型非多模态），降级空结果")
        status, source = "error", "error"
        description, candidate_poi, confidence, error = "", None, 0.0, "photo agent unavailable or parse failed"

    uncertain = source != "agent" or confidence < _LOW_CONFIDENCE_THRESHOLD or not candidate_poi
    recognition_status = "uncertain" if uncertain else "identified"
    low_confidence_hint = None
    next_actions: list[str] = []
    if uncertain:
        # A low-confidence candidate is not a fact and must not trigger RAG narration.
        candidate_poi = None
        low_confidence_hint = "未能确定照片中的地点，建议重拍或手动选择地点。"
        next_actions = ["retake", "manual_select"]

    # ── 讲解 seam：only a high-confidence canonical POI may trigger guide/RAG ──
    explanation = _explain(description, candidate_poi, language=language) if not uncertain else None

    # ── guide → reviewer 管道：讲解正文过审（block → 安全 fallback，不外泄）──
    photo_review = None
    if explanation and (explanation.get("text") or "").strip():
        explanation["text"], photo_review = _apply_review(explanation["text"], path="photo")

    record_trace(
        kind="guide.photo",
        status=status,
        agent_id="photo" if source == "agent" else None,
        input_summary=f"image {len(raw)}B {file.content_type}",
        output_summary=(description or "")[:200],
        latency_ms=latency_ms,
        extra={
            "language": language,
            "candidate_poi": candidate_poi,
            "confidence": confidence,
            "explained": explanation is not None,
            "recognition_status": recognition_status,
        },
    )

    return {
        "description": description,
        "candidate_poi": candidate_poi,
        "confidence": confidence,
        "explanation": explanation,  # guide agent 启用且成功时有值；否则 null
        "review": photo_review,      # guide→reviewer 管道裁定（explanation 为空时为 null）
        "ai_generated": True,
        "source_type": "ai",
        "scrubbed": True,
        "source": source,
        "error": error,
        "recognition_status": recognition_status,
        "low_confidence_hint": low_confidence_hint,
        "next_actions": next_actions,
        "manual_selection_endpoint": "/api/v1/pois?q=<keyword>",
    }


@router.post("/generate", dependencies=[Depends(rate_limit("text"))])
def generate(req: GuideRequest) -> dict:
    """POI + 偏好 → 文化讲解（RAG 取料 → guide agent；agent 不可用降级空讲解，不 500）。"""
    if not settings.guide_agent_enabled:
        raise HTTPException(
            status_code=503,
            detail="guide disabled (need guide agent in QwenPaw + GUIDE_AGENT_ENABLED=true)",
        )
    poi_name, material = _gather_material(req.poi, req.poi)
    if not material:
        raise HTTPException(status_code=404, detail=f"找不到 POI 资料：{req.poi}")

    t0 = time.perf_counter()
    expl = guide_agent.generate(poi_name, material=material, language=req.language, interests=req.interests)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    if expl is None:
        logger.info("guide agent 不可用或解析失败，降级空讲解")
        record_trace(kind="guide.generate", status="error", input_summary=req.poi[:200], latency_ms=latency_ms)
        return {
            "text": "",
            "source_type": "ai",
            "confidence": 0.0,
            "ai_generated": True,
            "language": req.language,
            "source": "error",
            "error": "guide agent unavailable",
        }

    record_trace(
        kind="guide.generate",
        status="ok",
        agent_id="guide",
        input_summary=req.poi[:200],
        output_summary=expl.text[:200],
        latency_ms=latency_ms,
        extra={"source_type": expl.source_type, "confidence": expl.confidence},
    )

    # ── guide → reviewer 管道：讲解正文过审（block → 安全 fallback 拦截，不外泄）──
    out_text, review = _apply_review(expl.text, path="generate")
    blocked = review.get("decision") == "block"

    return {
        "text": out_text,
        "source_type": expl.source_type,
        "confidence": expl.confidence,
        "ai_generated": expl.ai_generated,
        "language": expl.language,
        "source": "agent",
        "review": review,
        "blocked": blocked,
        "error": None,
    }


@router.post("/tts", response_model=TTSResponse, dependencies=[Depends(rate_limit("expensive"))])
def tts(req: TTSRequest) -> TTSResponse:
    """Text-to-speech with fixed four-language voices and private OSS delivery."""
    try:
        result = synthesize_to_oss(req.text, req.language)
    except TTSUnavailableError as exc:
        record_audit(
            kind="guide.tts",
            status="unavailable",
            input_chars=len(req.text),
            metadata={"language": req.language},
        )
        raise HTTPException(status_code=503, detail=f"TTS unavailable: {exc}; retry later") from exc
    record_audit(
        kind="guide.tts",
        status="ok",
        input_chars=len(req.text),
        metadata={"language": req.language, "voice": result["voice"]},
    )
    return TTSResponse(
        audio_url=str(result["audio_url"]),
        expires_in=int(result["expires_in"]),
        content_type=str(result["content_type"]),
        language=req.language,
        voice=str(result["voice"]),
    )
