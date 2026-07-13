"""拍照识别接口（Phase 4 竖切，QwenPaw ``photo`` agent 驱动）。

链路：上传图 → ``scrub`` 脱敏（EXIF 剥离 + 人脸模糊）→ 写临时文件 → QwenPaw ``photo``
agent（用 ``view_image`` 工具看图）→ ``{description, candidate_poi, confidence}``。

**讲解**（RAG + guide agent）是依赖同事 guide agent 的部分，本竖切**留出接口但暂不接**
（见下方 ``_explain`` seam 与响应里的 ``explanation`` 字段恒为 null）。

失败纪律（对齐 routes/intent）：开关关 → 503；photo agent 抖动或模型非多模态 → 不抛穿，
返回 ``confidence=0`` + ``error`` 字段，仍 200。
"""

from __future__ import annotations

import logging
import os
import tempfile
import time

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.agents import photo_agent
from app.core.config import settings
from app.observability.trace import record_trace
from app.tools.scrub import scrub

logger = logging.getLogger("macau_storywalk.guide")

router = APIRouter(prefix="/api/v1/guide", tags=["guide"])

_ALLOW_MIME = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 8 * 1024 * 1024  # 8MB


def _explain(description: str, candidate_poi: str | None, *, language: str) -> dict | None:
    """讲解 seam —— 依赖同事的 guide agent + RAG，本竖切**暂留空**。

    等 guide agent（agent-id ``guide``，技能 ``macau-guide``）就位后，这里应：
        from rag.retrieve import retrieve
        docs = retrieve(candidate_poi or description, k=4)
        return guide_agent.generate(poi=candidate_poi, chunks=docs, language=language)
    # 返回 {text, source_type, confidence, ai_generated, language}

    现在恒返回 None —— 前端据此只展示「识别结果」，不展示「讲解」。
    """
    return None


@router.post("/photo")
async def photo(
    file: UploadFile = File(..., description="用户在澳门街头拍的照片（jpeg/png/webp，≤8MB）"),
    language: str = Query("zh-CN", description="描述/讲解语言：zh-CN/zh-TW/en/pt"),
) -> dict:
    """拍照 → 这是啥（QwenPaw photo agent 看图；讲解暂留空）。"""
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

    # ── SEAM：讲解（guide agent + RAG）—— 本竖切暂留空 ──
    explanation = _explain(description, candidate_poi, language=language)
    # ────────────────────────────────────────────────────

    record_trace(
        kind="guide.photo",
        status=status,
        agent_id="photo" if source == "agent" else None,
        input_summary=f"image {len(raw)}B {file.content_type}",
        output_summary=(description or "")[:200],
        latency_ms=latency_ms,
        extra={"language": language, "candidate_poi": candidate_poi, "confidence": confidence},
    )

    return {
        "description": description,
        "candidate_poi": candidate_poi,
        "confidence": confidence,
        "explanation": explanation,  # None 直到 guide agent 接入
        "ai_generated": True,
        "source_type": "ai",
        "scrubbed": True,
        "source": source,
        "error": error,
    }
