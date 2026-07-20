"""拍照识别 / 文化讲解接口（Phase 4 + P2，QwenPaw ``photo`` / ``guide`` agent 驱动）。

- ``POST /api/v1/guide/photo``：上传图 → scrub 脱敏 → photo agent 看图识别 → guide agent 讲解
  （识别恒走 photo agent；讲解走 guide agent + RAG，guide 未启用则 ``explanation`` 留空）。
- ``POST /api/v1/guide/generate``：POI 名/id + 偏好 → RAG 取料 → guide agent 讲解。
- ``POST /api/v1/guide/trigger``：位置 → 最近 POI 提示（用户确认后才生成讲解）。

讲解素材策略（``_gather_material``）：candidate_poi 已点名 → ``get_poi_material`` 精确取整 POI
（最稳，不靠向量）；否则 ``retrieve()`` 向量找相关 POI 兜底。
Ask 追问（``/ask``）为 **web-first**：短超时联网为主，``_gather_material_fast`` 仅作本地点缀/兜底。

失败纪律（对齐 routes/intent）：开关关 → 503；agent 抖动 / 解析失败 → 不抛穿，
返回空结果 + ``error`` 字段，仍 200。
"""

from __future__ import annotations

import logging
import os
import re
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

from .preset_script import build_preset_narration
from .trigger_state import trigger_state
from .tts import TTSUnavailableError, VOICE_BY_LANGUAGE, synthesize_to_oss
from .web_search import format_web_material, search_web_multi

# rag/ 在仓库根（不在 backend/app 内）；config.py 导入时已把仓库根加进 sys.path
from rag.retrieve import get_poi_material, retrieve

logger = logging.getLogger("macau_storywalk.guide")

router = APIRouter(prefix="/api/v1/guide", tags=["guide"])

_ALLOW_MIME = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 8 * 1024 * 1024  # 8MB

# block 裁定下，讲解正文替换为这句安全 fallback（原始不安全文本不外泄）
_BLOCK_FALLBACK = "（该讲解未通过安全审核，已暂缓展示，请稍后重试。）"
_LOW_CONFIDENCE_THRESHOLD = 0.6

_ASK_FALLBACK = {
    "zh-CN": "根据现有资料，我暂时只能这样回答：{snippet}",
    "zh-TW": "根據現有資料，我暫時只能這樣回答：{snippet}",
    "en": "From the materials we have, here’s what I can say: {snippet}",
    "pt": "Com o material disponível, posso dizer: {snippet}",
}
# 仅在本地 + 联网都失败时使用（有联网能力时不要过早甩出「手头没有资料」）
_ASK_EMPTY = {
    "zh-CN": "本地和公开网页都没找到可靠答案。你可以换个问法，或拍一张现场照片让我辨认。",
    "zh-TW": "本地和公開網頁都沒找到可靠答案。你可以換個問法，或拍一張現場照片讓我辨認。",
    "en": "Neither local notes nor public web sources had a solid answer. Try rephrasing, or upload a photo.",
    "pt": "Nem as notas locais nem a web pública tiveram uma resposta sólida. Reformule, ou envie uma foto.",
}
_PURPOSE_INTENT = re.compile(
    r"(干什么|做什麼|做什么|用途|原来|原來|原先|前身|功能|用来|用來|作什麼|作什么|what\s+was|used\s+for|original)",
    re.IGNORECASE,
)
_PURPOSE_HINTS = ("原为", "原為", "前身", "曾是", "用作", "建成", "历史", "歷史", "教堂", "学院", "學院")
_ASK_STOP = {
    "这个",
    "那个",
    "什么",
    "什麼",
    "为什么",
    "為什麼",
    "怎么",
    "怎樣",
    "怎样",
    "上面",
    "下面",
    "有没有",
    "有沒有",
    "可以",
    "一下",
    "请问",
    "請問",
    "告诉",
    "告訴",
    "我想",
    "know",
    "what",
    "when",
    "where",
    "which",
    "about",
    "please",
    "this",
    "that",
    "building",
}
_REFUSAL_MARKERS = (
    "手头资料里没有",
    "手頭資料裡沒有",
    "资料里没有直接",
    "資料裡沒有直接",
    "没有直接答案",
    "沒有直接答案",
    "本地和公开网页都没找到",
    "本地和公開網頁都沒找到",
    "no direct answer",
    "don't have a direct",
    "do not have a direct",
    "não há resposta direta",
)

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


def _gather_material_fast(poi: str, *, language: str, interests: list[str] | None) -> tuple[str, str]:
    """Ask 用的轻量本地取料：精确 POI / 预设话术，不跑向量检索（避免拖慢 web-first）。"""
    got = get_poi_material(poi)
    if got and got[1]:
        return got
    preset = build_preset_narration(poi, language=language, interests=interests)
    if preset and preset.get("text"):
        name = str(preset.get("poi_name") or poi)
        return name, str(preset["text"])
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
    # 行程下一站名称；传空字符串表示末站；省略则无行程收尾语
    next_stop: str | None = None

    @field_validator("poi")
    @classmethod
    def sanitize_poi(cls, value: str) -> str:
        value = sanitize_untrusted_text(value, max_length=255)
        if not value:
            raise ValueError("poi must not be blank")
        return value

    @field_validator("next_stop")
    @classmethod
    def sanitize_next_stop(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_untrusted_text(value, max_length=255)


class GuideAskRequest(BaseModel):
    poi: str = Field(min_length=1, max_length=255)
    question: str = Field(min_length=1, max_length=1000)
    language: str = "zh-CN"
    interests: list[str] | None = None

    @field_validator("poi")
    @classmethod
    def sanitize_poi(cls, value: str) -> str:
        value = sanitize_untrusted_text(value, max_length=255)
        if not value:
            raise ValueError("poi must not be blank")
        return value

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, value: str) -> str:
        value = sanitize_untrusted_text(value, max_length=1000)
        if not value:
            raise ValueError("question must not be blank")
        return value


def _question_tokens(question: str) -> list[str]:
    """从追问里抽检索词。中文无空格时切 2–4 字片，避免整句当一个 token。"""
    q = (question or "").strip().lower()
    if not q:
        return []
    parts = [p for p in re.split(r"[\s,，。？?！!、；;：:]+", q) if p]
    tokens: list[str] = []
    for part in parts:
        if re.search(r"[\u4e00-\u9fff]", part):
            for run in re.findall(r"[\u4e00-\u9fff]+", part):
                if len(run) >= 2:
                    tokens.append(run)
                for n in (2, 3, 4):
                    if len(run) < n:
                        continue
                    for i in range(len(run) - n + 1):
                        tokens.append(run[i : i + n])
            tokens.extend(re.findall(r"[a-z0-9]{2,}", part))
        elif len(part) >= 2:
            tokens.append(part)
    if _PURPOSE_INTENT.search(q):
        tokens.extend(_PURPOSE_HINTS)
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t in _ASK_STOP or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _looks_like_refusal(text: str) -> bool:
    low = (text or "").strip().lower()
    if not low:
        return True
    return any(m.lower() in low for m in _REFUSAL_MARKERS)


def _material_snippet_answer(
    question: str, material: str, *, language: str
) -> tuple[str, bool]:
    """从资料挑相关句。返回 (answer, is_weak)。weak=关键词几乎对不上。"""
    if not material.strip():
        return "", True
    tokens = _question_tokens(question)
    sentences = [
        s.strip()
        for s in re.split(r"[。！？!?\n]+", material)
        if s.strip()
    ]
    scored: list[tuple[int, str]] = []
    for s in sentences:
        sl = s.lower()
        # 长 token 权重大，减少无意义 2-gram 刷分
        score = 0
        for t in tokens:
            if t.lower() in sl:
                score += 3 if len(t) >= 3 else 1
        if score:
            scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)
    weak = True
    if tokens and scored:
        top = scored[0][0]
        # 命中用途/历史暗示或累计分够高 → 本地可用
        if top >= 3 or (top >= 2 and len(tokens) <= 3):
            weak = False
        elif top >= 1 and any(h in scored[0][1] for h in _PURPOSE_HINTS):
            weak = False
        else:
            weak = True
    elif tokens and not scored:
        weak = True
    elif not tokens:
        weak = True

    picked = [s for _, s in scored[:2]] or (sentences[:2] if not tokens else [])
    cleaned = []
    for s in picked:
        cleaned.append(
            re.sub(
                r"^(intro|history|architecture|story|observation_tips)\s*:\s*",
                "",
                s,
                flags=re.IGNORECASE,
            ).strip()
        )
    snippet = "。".join(c for c in cleaned if c)
    if snippet and not snippet.endswith(("。", ".", "!", "？", "?")):
        snippet += "。"
    if not snippet:
        return "", True
    tmpl = _ASK_FALLBACK.get(language, _ASK_FALLBACK["zh-CN"])
    return tmpl.format(snippet=snippet), weak


def _web_search_queries(poi_name: str, question: str, *, limit: int = 2) -> list[str]:
    """构造联网检索查询（默认最多 2 条，控延迟）。

    优先：``POI + 问题``；用途类追问再加 ``POI 历史/原为``；否则 POI 名本身。
    """
    poi = (poi_name or "").strip()
    q = (question or "").strip()
    queries: list[str] = []
    if poi and q:
        queries.append(f"{poi} {q}")
    if poi and _PURPOSE_INTENT.search(q):
        queries.append(f"{poi} 历史 原为")
    elif poi:
        queries.append(poi)
    elif q:
        queries.append(q)
    seen: set[str] = set()
    out: list[str] = []
    for item in queries:
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
        if len(out) >= limit:
            break
    return out


def _web_snippet_answer(
    question: str,
    hits: list[dict[str, str]],
    *,
    language: str,
    poi_name: str,
) -> str:
    if not hits:
        return _ASK_EMPTY.get(language, _ASK_EMPTY["zh-CN"])
    body = " ".join(str(h.get("snippet") or "") for h in hits[:2]).strip()
    # 压成较短口语段
    body = re.sub(r"\s+", " ", body)
    if len(body) > 420:
        body = body[:420].rstrip() + "…"
    cite = "；".join(
        f"{h.get('title') or '资料'}（{h.get('source') or 'web'}）" for h in hits[:2]
    )
    templates = {
        "zh-CN": f"关于「{poi_name}」与你的问题，结合公开资料可以这样理解：{body} 参考：{cite}。",
        "zh-TW": f"關於「{poi_name}」與你的問題，結合公開資料可以這樣理解：{body} 參考：{cite}。",
        "en": f"About {poi_name} and your question, public sources suggest: {body} Sources: {cite}.",
        "pt": f"Sobre {poi_name} e a sua pergunta, fontes públicas sugerem: {body} Fontes: {cite}.",
    }
    return templates.get(language, templates["zh-CN"])


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


@router.post("/ask", dependencies=[Depends(rate_limit("text"))])
def ask(
    req: GuideAskRequest,
    enhance: Annotated[
        bool, Query(description="是否调用 guide agent 深度回答（较慢）")
    ] = False,
    web: Annotated[
        bool, Query(description="是否联网检索公开百科（默认开启，作为主回答来源）")
    ] = True,
) -> dict:
    """就当前 POI 追问。

    **Web-first**（本地 KB 偏稀）：默认先短超时联网检索公开百科并合成答案；
    本地仅轻量取料作点缀/兜底，不挡联网。``enhance=true`` 时才调用 guide agent。
    """
    t0 = time.perf_counter()
    # 轻量本地（无向量检索）；不拖慢 web-first
    poi_name, material = _gather_material_fast(
        req.poi, language=req.language, interests=req.interests
    )
    display_name = poi_name or req.poi
    # web-first：本地无料仍可用 POI 名去搜；仅 web=false 且无料时 404
    if not material and not web:
        raise HTTPException(status_code=404, detail=f"找不到 POI 资料：{req.poi}")

    local_answer, weak = _material_snippet_answer(
        req.question, material, language=req.language
    )
    if not (local_answer or "").strip():
        weak = True

    answer_text = ""
    source = "empty"
    confidence = 0.3
    ai_generated = False
    error = None
    web_hits: list[dict[str, str]] = []
    used_web = False

    # ── 主路径：联网检索（短预算并行；agent 仅 enhance）──
    if web:
        queries = _web_search_queries(display_name, req.question, limit=2)
        web_hits = search_web_multi(
            queries, language=req.language, k=2, max_queries=2, budget_s=2.5
        )
        if web_hits:
            used_web = True
            web_material = format_web_material(web_hits, language=req.language)
            # 本地有料则作轻量点缀，不依赖相关度
            combined = (
                f"{material}\n\n{web_material}".strip() if material else web_material
            )
            web_answer = _web_snippet_answer(
                req.question,
                web_hits,
                language=req.language,
                poi_name=display_name,
            )

            if enhance and settings.guide_agent_enabled:
                expl = guide_agent.answer(
                    display_name,
                    req.question,
                    material=combined,
                    language=req.language,
                    interests=req.interests,
                )
                if (
                    expl
                    and expl.text.strip()
                    and not _looks_like_refusal(expl.text)
                ):
                    answer_text = expl.text
                    confidence = max(float(expl.confidence or 0.7), 0.7)
                    ai_generated = True
                    source = "agent+web"
                else:
                    answer_text = web_answer
                    source = "web"
                    confidence = 0.65
                    if expl is None:
                        error = "guide agent unavailable; served web snippets"
                    elif _looks_like_refusal(expl.text):
                        error = "guide agent refused; served web snippets"
            else:
                answer_text = web_answer
                source = "web"
                confidence = 0.65

    # ── 兜底：强相关本地摘录 / enhance 仅本地 / 空答案（不甩「手头没有」）──
    if not (answer_text or "").strip():
        if not weak and (local_answer or "").strip():
            answer_text = local_answer
            source = "rules"
            confidence = 0.55
            if enhance and settings.guide_agent_enabled and material.strip():
                expl = guide_agent.answer(
                    display_name,
                    req.question,
                    material=material,
                    language=req.language,
                    interests=req.interests,
                )
                if (
                    expl
                    and expl.text.strip()
                    and not _looks_like_refusal(expl.text)
                ):
                    answer_text = expl.text
                    confidence = expl.confidence
                    ai_generated = True
                    source = "agent"
                else:
                    error = "guide agent unavailable; served material snippet"
        else:
            answer_text = _ASK_EMPTY.get(req.language, _ASK_EMPTY["zh-CN"])
            confidence = 0.25
            source = "empty"

    # 拒答文案兜底（避免泄漏「手头资料里没有」；空答案模板本身含拒答标记，跳过）
    if source != "empty" and _looks_like_refusal(answer_text) and not used_web:
        answer_text = _ASK_EMPTY.get(req.language, _ASK_EMPTY["zh-CN"])
        confidence = min(confidence, 0.3)
        source = "empty"

    out_text, review = _apply_review(answer_text, path="ask")
    latency_ms = int((time.perf_counter() - t0) * 1000)
    record_trace(
        kind="guide.ask",
        status="ok",
        agent_id="guide" if source.startswith("agent") else None,
        input_summary=f"{req.poi}:{req.question[:120]}",
        output_summary=out_text[:200],
        latency_ms=latency_ms,
        extra={
            "source": source,
            "enhance": enhance,
            "web": used_web,
            "weak_local": weak,
            "web_hits": len(web_hits),
            "strategy": "web_first",
        },
    )
    return {
        "poi_name": display_name,
        "question": req.question,
        "text": out_text,
        "language": req.language,
        "source": source,
        "confidence": confidence,
        "ai_generated": ai_generated,
        "blocked": review.get("decision") == "block",
        "error": error,
        "review": review,
        "web_used": used_web,
        "web_sources": [
            {"title": h.get("title"), "url": h.get("url"), "source": h.get("source")}
            for h in web_hits[:3]
        ],
    }


@router.post("/generate", dependencies=[Depends(rate_limit("text"))])
def generate(
    req: GuideRequest,
    enhance: Annotated[bool, Query(description="是否再用 guide agent 深度改写（较慢）")] = False,
) -> dict:
    """POI + 偏好 → 文化讲解。

    默认走预设话术（POI 资料拼接 + 兴趣轻量个性化），毫秒级返回。
    ``enhance=true`` 且 guide agent 启用时，再调用 LLM 改写（可选）。
    """
    t0 = time.perf_counter()
    preset = build_preset_narration(
        req.poi,
        language=req.language,
        interests=req.interests,
        next_stop=req.next_stop,
    )
    if preset is None:
        # 回退：旧 gather 路径仍找不到则 404
        poi_name, material = _gather_material(req.poi, req.poi)
        if not material:
            raise HTTPException(status_code=404, detail=f"找不到 POI 资料：{req.poi}")
        preset = {
            "text": material.split("\n")[0][:500],
            "sections": [
                {
                    "id": "overview",
                    "body": material.split("\n")[0][:500],
                }
            ],
            "source_type": "ai",
            "confidence": 0.5,
            "ai_generated": False,
            "language": req.language,
            "source": "preset",
            "poi_name": poi_name or req.poi,
            "blocked": False,
            "error": None,
            "review": None,
        }

    # 快速路径：预设话术
    if not enhance or not settings.guide_agent_enabled:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        record_trace(
            kind="guide.generate",
            status="ok",
            agent_id=None,
            input_summary=req.poi[:200],
            output_summary=str(preset.get("text", ""))[:200],
            latency_ms=latency_ms,
            extra={"source": "preset", "interests": req.interests or []},
        )
        return preset

    # 可选增强：guide agent 改写预设稿
    poi_name, material = _gather_material(req.poi, req.poi)
    expl = guide_agent.generate(
        poi_name or str(preset.get("poi_name") or req.poi),
        material=material or str(preset.get("text") or ""),
        language=req.language,
        interests=req.interests,
    )
    latency_ms = int((time.perf_counter() - t0) * 1000)

    if expl is None or not expl.text.strip():
        record_trace(
            kind="guide.generate",
            status="preset_fallback",
            input_summary=req.poi[:200],
            latency_ms=latency_ms,
            extra={"error": "guide agent unavailable"},
        )
        preset["error"] = "guide agent unavailable; served preset"
        return preset

    record_trace(
        kind="guide.generate",
        status="ok",
        agent_id="guide",
        input_summary=req.poi[:200],
        output_summary=expl.text[:200],
        latency_ms=latency_ms,
        extra={"source_type": expl.source_type, "confidence": expl.confidence, "enhanced": True},
    )

    out_text, review = _apply_review(expl.text, path="generate")
    blocked = review.get("decision") == "block"
    # Keep POI-field sections for pictorial UI; agent rewrite only replaces flat TTS text.
    return {
        "text": out_text,
        "sections": preset.get("sections") or [],
        "source_type": expl.source_type,
        "confidence": expl.confidence,
        "ai_generated": expl.ai_generated,
        "language": expl.language,
        "source": "agent",
        "poi_name": preset.get("poi_name"),
        "poi_id": preset.get("poi_id"),
        "next_stop": preset.get("next_stop"),
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
