"""拍照识别 / 文化讲解接口（Phase 4 + P2，QwenPaw ``photo`` / ``guide`` agent 驱动）。

- ``POST /api/v1/guide/photo``：上传图 → scrub 脱敏 → photo agent 看图识别 → guide agent 讲解
  （识别恒走 photo agent；讲解走 guide agent + RAG，guide 未启用则 ``explanation`` 留空）。
- ``POST /api/v1/guide/generate``：POI 名/id + 偏好 → RAG 取料 → guide agent 讲解。

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

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.agents import guide_agent, photo_agent
from app.core.config import settings
from app.features.review.api import review_text
from app.observability.trace import record_trace
from app.tools.scrub import scrub

# rag/ 在仓库根（不在 backend/app 内）；config.py 导入时已把仓库根加进 sys.path
from rag.retrieve import get_poi_material, retrieve

logger = logging.getLogger("macau_storywalk.guide")

router = APIRouter(prefix="/api/v1/guide", tags=["guide"])

_ALLOW_MIME = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 8 * 1024 * 1024  # 8MB

# block 裁定下，讲解正文替换为这句安全 fallback（原始不安全文本不外泄）
_BLOCK_FALLBACK = "（该讲解未通过安全审核，已暂缓展示，请稍后重试。）"


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
    poi: str                             # POI 名字（中/英/葡）或 id
    language: str = "zh-CN"
    interests: list[str] | None = None   # history / architecture / food / photo / culture


@router.post("/photo")
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

    # ── 讲解 seam：guide agent + RAG（guide 未启用 / 失败 → explanation=null）──
    explanation = _explain(description, candidate_poi, language=language)

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
    }


@router.post("/generate")
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
