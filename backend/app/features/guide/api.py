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
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.agents import guide_agent, photo_agent
from app.core.config import settings
from app.core.security import optional_user_id
from app.db.session import get_db
from app.features.pois.models import NearbyPoiResponse
from app.features.pois.service import PoiService
from app.features.stories.content import StoryContentError, StoryNotFoundError
from app.features.stories.engine import StoryChapterConflictError
from app.features.stories.service import (
    StoryContentVersionError,
    StorySessionNotFoundError,
    StorySessionOwnershipError,
)
from app.features.memoirs.models import MemoirCreateRequest
from app.features.memoirs.service import (
    MemoirError,
    MemoirNotFoundError,
    memoir_service,
)
from app.features.review.api import review_text
from app.guardrails.runtime import rate_limit, record_audit, sanitize_untrusted_text
from app.observability.trace import record_trace
from app.tools.scrub import scrub

from .preset_script import (
    build_preset_narration,
    poi_names_by_language,
    poi_names_for,
    poi_official_hits_for,
)
from .models import GuideConversationMessage, GuideStoryReference
from .service import resolve_story_guide_context, story_guide_fallback
from .trigger_state import trigger_state
from .tts import TTSUnavailableError, VOICE_BY_LANGUAGE, local_audio_path, synthesize_to_oss
from .web_search import filter_relevant_hits, format_web_material, search_web_multi

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
    "zh-CN": "暂未从本地资料或公开网页检索到可靠的相关资料。你可以把问题说得更具体一些，或拍一张现场照片让我辨认。",
    "zh-TW": "暫未從本地資料或公開網頁檢索到可靠的相關資料。你可以把問題說得更具體一些，或拍一張現場照片讓我辨認。",
    "en": "I couldn't retrieve reliable, relevant material from the local notes or public sources. Try a more specific question, or upload a photo.",
    "pt": "Não consegui encontrar material fiável e relevante nas notas locais ou em fontes públicas. Faça uma pergunta mais específica ou envie uma fotografia.",
}
_PURPOSE_INTENT = re.compile(
    r"(干什么|做什麼|做什么|用途|原来|原來|原先|前身|功能|用来|用來|作什麼|作什么|what\s+was|used\s+for|original)",
    re.IGNORECASE,
)
_PURPOSE_HINTS = ("原为", "原為", "前身", "曾是", "用作", "建成", "历史", "歷史", "教堂", "学院", "學院")
_TEMPORAL_INTENT = re.compile(
    r"(什么时候|甚麼時候|何时|何時|哪年|建立|建成|落成|启用|啟用|开放|開放|通车|通車|"
    r"when\s+(?:was|did)|what\s+year|built|completed|established|opened|inaugurated|"
    r"quando|constru[íi]d|conclu[íi]d|inaugurad|abert)",
    re.IGNORECASE,
)
_TEMPORAL_HINTS = (
    "建立",
    "建成",
    "落成",
    "启用",
    "啟用",
    "开放",
    "開放",
    "通车",
    "通車",
    "施工",
    "built",
    "completed",
    "opened",
    "construction",
    "inaugurated",
)
_TEMPORAL_FACT = re.compile(
    r"(?:\b(?:18|19|20)\d{2}\b|建成|落成|启用|啟用|开放|開放|通车|通車|"
    r"built|completed|opened|inaugurated|construction|constru[íi]d|conclu[íi]d)",
    re.IGNORECASE,
)
_HISTORY_CHANGE_INTENT = re.compile(
    r"(变化|變化|演变|演變|变迁|變遷|沿革|修缮|修繕|修复|修復|重建|改建|扩建|擴建|"
    r"changed?|changes|evol(?:ve|ved|ution)|development|restor(?:e|ed|ation)|rebuilt?|"
    r"mudan[çc]as?|evolu[çc][ãa]o|restaur(?:ado|a[çc][ãa]o)|reconstru[íi]d)",
    re.IGNORECASE,
)
_TRADITIONAL_MARKERS = set("這麼時為麼開啟麼裡與還體來說請問過於從將會後發現處")
_PORTUGUESE_MARKERS = {
    "a",
    "as",
    "como",
    "com",
    "de",
    "do",
    "dos",
    "em",
    "esta",
    "este",
    "foi",
    "o",
    "os",
    "para",
    "por",
    "quando",
    "que",
    "qual",
    "uma",
}
_QUERY_INTENT_TERMS: list[tuple[re.Pattern[str], dict[str, str]]] = [
    (
        _TEMPORAL_INTENT,
        {
            "zh-CN": "建设 建成 启用 开放 时间",
            "en": "construction completion opening date",
            "pt": "construção conclusão inauguração data",
        },
    ),
    (
        _PURPOSE_INTENT,
        {
            "zh-CN": "历史 原来用途 功能",
            "en": "history original purpose function",
            "pt": "história finalidade original função",
        },
    ),
    (
        re.compile(
            rf"历史|歷史|过去|過去|history|historical|história|{_HISTORY_CHANGE_INTENT.pattern}",
            re.IGNORECASE,
        ),
        {
            "zh-CN": "历史 沿革 变化 修缮 重建",
            "en": "history changes development restoration rebuilding",
            "pt": "história evolução mudanças restauro reconstrução",
        },
    ),
    (
        re.compile(r"建筑|建築|设计|設計|风格|風格|architecture|design|arquitetura", re.IGNORECASE),
        {"zh-CN": "建筑 设计 风格", "en": "architecture design style", "pt": "arquitetura estilo"},
    ),
    (
        re.compile(r"开放时间|開放時間|几点|幾點|hours|opening time|horário", re.IGNORECASE),
        {"zh-CN": "开放时间 营业时间", "en": "opening hours", "pt": "horário de funcionamento"},
    ),
    (
        re.compile(r"门票|門票|票价|票價|多少钱|多少錢|ticket|price|bilhete|preço", re.IGNORECASE),
        {"zh-CN": "门票 票价", "en": "ticket admission price", "pt": "bilhete preço entrada"},
    ),
    (
        re.compile(r"交通|怎么去|怎麼去|巴士|公交|transport|bus|como chegar|autocarro", re.IGNORECASE),
        {"zh-CN": "交通 巴士 如何前往", "en": "transport bus how to get there", "pt": "transporte autocarro como chegar"},
    ),
]
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
    "暂未从本地资料或公开网页检索到",
    "暫未從本地資料或公開網頁檢索到",
    "couldn't retrieve reliable, relevant material",
    "não consegui encontrar material fiável e relevante",
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


def _guide_language_matches(explanation: object, language: str) -> bool:
    """Reject an enhanced foreign-language result that leaks Chinese source text."""
    return guide_agent.language_matches(explanation, language)


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
    preset = build_preset_narration(poi, language=language, interests=interests)
    if language in {"en", "pt"} and preset and preset.get("text"):
        name = str(preset.get("poi_name") or poi)
        return name, str(preset["text"])
    got = get_poi_material(poi)
    if got and got[1]:
        return got
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
    travel_type: list[str] | None = None  # family / solo / …（偏好个性化）
    # 行程下一站名称；传空字符串表示末站；省略则无行程收尾语
    next_stop: str | None = None
    # 可选：来自行程腿的下一站距离 / 步行时间文案（未知勿编造，由客户端传入）
    next_distance: str | None = None
    next_walk_time: str | None = None

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

    @field_validator("next_distance", "next_walk_time")
    @classmethod
    def sanitize_next_meta(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_untrusted_text(value, max_length=64)


class GuideAskRequest(BaseModel):
    poi: str = Field(min_length=1, max_length=255)
    question: str = Field(min_length=1, max_length=1000)
    language: str = "zh-CN"
    interests: list[str] | None = None
    story_context: GuideStoryReference | None = None
    history: list[GuideConversationMessage] = Field(default_factory=list, max_length=8)

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
    if _TEMPORAL_INTENT.search(q):
        tokens.extend(_TEMPORAL_HINTS)
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t in _ASK_STOP or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _search_language(language: str) -> str:
    if language.startswith("zh"):
        return "zh-CN"
    return language if language in {"en", "pt"} else "en"


def _detect_question_language(question: str) -> str:
    text = (question or "").strip()
    if re.search(r"[\u3400-\u9fff]", text):
        return "zh-TW" if sum(char in _TRADITIONAL_MARKERS for char in text) >= 2 else "zh-CN"
    words = set(re.findall(r"[a-zà-ÿ]+", text.lower()))
    portuguese_score = len(words & _PORTUGUESE_MARKERS)
    if re.search(r"[ãõçáéíóúâêôà]", text.lower()) or portuguese_score >= 2:
        return "pt"
    return "en"


def _fallback_query_translations(question: str, input_language: str) -> dict[str, str]:
    source = _search_language(input_language)
    translated = {source: question.strip()}
    for pattern, terms in _QUERY_INTENT_TERMS:
        if pattern.search(question):
            for language, value in terms.items():
                translated.setdefault(language, value)
            break
    return translated


def _search_query_sets(
    query_sets: dict[str, list[str]],
    *,
    k: int = 2,
    budget_s: float = 3.5,
) -> list[dict[str, str]]:
    """Search translated query sets concurrently while preserving language priority."""
    ordered = [(language, queries) for language, queries in query_sets.items() if queries]
    if not ordered:
        return []
    by_language: dict[str, list[dict[str, str]]] = {}
    with ThreadPoolExecutor(max_workers=len(ordered)) as pool:
        futures = {
            pool.submit(
                search_web_multi,
                queries,
                language=language,
                k=k,
                max_queries=2,
                budget_s=min(2.5, budget_s),
            ): language
            for language, queries in ordered
        }
        try:
            for future in as_completed(futures, timeout=budget_s):
                language = futures[future]
                try:
                    hits = future.result()
                except Exception as exc:  # noqa: BLE001
                    logger.info("多语言检索失败（%s）：%s", language, exc)
                    continue
                by_language[language] = [
                    {**hit, "search_language": language} for hit in hits
                ]
        except TimeoutError:
            logger.info("多语言检索预算用尽（%.1fs）", budget_s)

    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for language, _queries in ordered:
        for hit in by_language.get(language, []):
            key = str(hit.get("url") or hit.get("title") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            results.append(hit)
    return results


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
        for s in re.split(
            r"[。！？!?]+|\n+|(?<=[.!?])\s+(?=[A-ZÀ-Þ])",
            material,
        )
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
    separator = " " if language in {"en", "pt"} else "。"
    snippet = separator.join(c for c in cleaned if c)
    if snippet and not snippet.endswith(("。", ".", "!", "？", "?")):
        snippet += "。"
    if not snippet:
        return "", True
    tmpl = _ASK_FALLBACK.get(language, _ASK_FALLBACK["zh-CN"])
    return tmpl.format(snippet=snippet), weak


def _expanded_search_names(poi_name: str, aliases: list[str] | None = None) -> list[str]:
    names = [poi_name, *(aliases or [])]
    expanded: list[str] = []
    for raw in names:
        name = (raw or "").strip()
        if not name:
            continue
        if re.search(r"\bHZMB\b", name, re.IGNORECASE):
            expanded.extend(
                [
                    "Hong Kong-Zhuhai-Macau Bridge",
                    "Hong Kong-Zhuhai-Macao Bridge",
                    "Hong Kong-Zhuhai-Macao Bridge Macao Port",
                ]
            )
        if "Hong Kong-Zhuhai-Macao Bridge" in name:
            expanded.extend(
                [
                    "Hong Kong-Zhuhai-Macau Bridge",
                    "Hong Kong-Zhuhai-Macao Bridge",
                    name.replace("Hong Kong-Zhuhai-Macao", "Hong Kong-Zhuhai-Macau"),
                ]
            )
        expanded.append(name)
    return list(dict.fromkeys(expanded))


def _web_search_queries(
    poi_name: str,
    question: str,
    *,
    aliases: list[str] | None = None,
    language: str = "zh-CN",
    limit: int = 2,
) -> list[str]:
    """构造联网检索查询（默认最多 2 条，控延迟）。

    优先：``POI + 问题``；用途类追问再加 ``POI 历史/原为``；否则 POI 名本身。
    """
    names = _expanded_search_names(poi_name, aliases)
    poi = (poi_name or "").strip()
    q = (question or "").strip()
    queries: list[str] = []
    temporal = bool(_TEMPORAL_INTENT.search(q))
    history_change = bool(_HISTORY_CHANGE_INTENT.search(q))
    if temporal and names:
        suffix = {
            "en": "built completed opened inauguration date",
            "pt": "construção conclusão inauguração data",
        }.get(language, "建设 建成 启用 开放 时间")
        preferred = [
            name
            for name in names
            if (language.startswith("zh")) == bool(re.search(r"[\u3400-\u9fff]", name))
        ] or names
        primary = preferred[0]
        queries.extend([primary, f"{primary} {suffix}"])
    elif history_change and names:
        suffix = {
            "en": "history changes development restoration rebuilding",
            "pt": "história evolução mudanças restauro reconstrução",
        }.get(language, "历史 沿革 变化 修缮 重建")
        preferred = [
            name
            for name in names
            if (language.startswith("zh")) == bool(re.search(r"[\u3400-\u9fff]", name))
        ] or names
        primary = preferred[0]
        queries.extend([f"{primary} {suffix}", primary])
    elif poi and q:
        same_script = language.startswith("zh") or not re.search(r"[\u3400-\u9fff]", q)
        queries.append(f"{poi} {q}" if same_script else poi)
    if poi and _PURPOSE_INTENT.search(q):
        purpose_suffix = "history original use" if language == "en" else "历史 原为"
        queries.append(f"{poi} {purpose_suffix}")
    elif poi and not temporal:
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
    target_search_language = _search_language(language)
    annotated_hits = [hit for hit in hits if hit.get("search_language")]
    same_language_hits = [
        hit
        for hit in annotated_hits
        if _search_language(str(hit.get("search_language"))) == target_search_language
    ]
    if same_language_hits:
        usable_hits = same_language_hits[:2]
    elif annotated_hits:
        return _ASK_EMPTY.get(language, _ASK_EMPTY["zh-CN"])
    else:
        usable_hits = hits[:2]
    if language in {"en", "pt"}:
        usable_hits = [
            h
            for h in usable_hits
            if re.search(
                r"[\u3400-\u9fff]",
                f"{h.get('title') or ''} {h.get('snippet') or ''}",
            )
            is None
        ]
    if not usable_hits:
        return _ASK_EMPTY.get(language, _ASK_EMPTY["zh-CN"])
    snippets = [str(h.get("snippet") or "").strip() for h in usable_hits]
    if _TEMPORAL_INTENT.search(question):
        focused: list[str] = []
        for snippet in snippets:
            sentences = [
                sentence.strip()
                for sentence in re.split(r"(?<=[。！？.!?])\s+", snippet)
                if sentence.strip()
            ]
            focused.extend(sentence for sentence in sentences if _TEMPORAL_FACT.search(sentence))
        if focused:
            snippets = focused[:3]
    body = " ".join(snippets).strip()
    # 压成较短口语段
    body = re.sub(r"\s+", " ", body)
    if len(body) > 420:
        body = body[:420].rstrip() + "…"
    source_label = {"en": "Source", "pt": "Fonte"}.get(language, "资料")
    if language in {"en", "pt"}:
        cite = "; ".join(
            f"{h.get('title') or source_label} ({h.get('source') or 'web'})"
            for h in usable_hits
        )
    else:
        cite = "；".join(
            f"{h.get('title') or source_label}（{h.get('source') or 'web'}）"
            for h in usable_hits
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
    trip_id: str | None = Query(default=None, description="当前登录用户的行程 ID"),
    poi_id: str | None = Query(default=None, description="Guide 当前 POI ID"),
    user_id: str | None = Depends(optional_user_id),
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

    # 脱敏后的图字节直接交给 photo agent（其内部 upload_media 上传进 QwenPaw 工作区，
    # 宿主可读；不再写容器内临时文件——宿主 QwenPaw 看不见容器路径）
    t0 = time.perf_counter()
    recog = photo_agent.recognize(scrubbed, language=language)
    latency_ms = int((time.perf_counter() - t0) * 1000)

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

    saved_to_memoir = False
    memoir_id = None
    memoir_photo_id = None
    memoir_save_error = None
    if not uncertain and user_id and trip_id and poi_id:
        try:
            try:
                memoir = memoir_service.get_by_trip(trip_id, user_id)
            except MemoirNotFoundError:
                memoir = memoir_service.create(
                    trip_id,
                    user_id,
                    MemoirCreateRequest(style="diary", language=language),
                )
            saved_photo = memoir_service.add_photo(
                memoir.memoir_id,
                user_id,
                data=scrubbed,
                filename=f"guide-{poi_id}.jpg",
                content_type="image/jpeg",
                poi_id=poi_id,
                # Guide cannot reliably infer whether a blurred face was present.
                # Keep these photos private in shared memoirs by default.
                has_people=True,
            )
            saved_to_memoir = True
            memoir_id = memoir.memoir_id
            memoir_photo_id = saved_photo.photo_id
        except MemoirError as exc:
            memoir_save_error = str(exc)
            logger.info("Guide photo was recognized but not saved to memoir: %s", exc)

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
        "saved_to_memoir": saved_to_memoir,
        "memoir_id": memoir_id,
        "memoir_photo_id": memoir_photo_id,
        "memoir_save_error": memoir_save_error,
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
    user_id: str | None = Depends(optional_user_id),
) -> dict:
    """就当前 POI 追问。

    **Web-first**（本地 KB 偏稀）：默认先短超时联网检索公开百科并合成答案；
    本地仅轻量取料作点缀/兜底，不挡联网。跨语言提问会自动调用 guide agent，
    将多语言检索材料统一合成为个人中心设定的语言；``enhance=true`` 可强制深度回答。
    StoryWalk 提交会话/章节引用后，服务端加载已解锁剧情，自动调用同一个 guide agent。
    """
    t0 = time.perf_counter()
    story_context = None
    if req.story_context is not None:
        if not user_id:
            raise HTTPException(status_code=401, detail="missing story session authentication")
        try:
            story_context = resolve_story_guide_context(
                req.story_context, user_id, language=req.language
            )
        except StorySessionOwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (StorySessionNotFoundError, StoryNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (StoryChapterConflictError, StoryContentVersionError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except StoryContentError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        req = req.model_copy(update={"poi": story_context.poi_id or story_context.poi_name})
    # Keep question-only retrieval and the ordinary Guide contract unchanged.
    answer_context = {}
    if story_context is not None:
        answer_context["story_context"] = story_context
    if req.history:
        answer_context["history"] = req.history
    # 轻量本地（无向量检索）；不拖慢 web-first
    poi_name, material = _gather_material_fast(
        req.poi, language=req.language, interests=req.interests
    )
    display_name = poi_name or req.poi
    input_language = _detect_question_language(req.question)
    output_search_language = _search_language(req.language)
    # web-first：本地无料仍可用 POI 名去搜；仅 web=false 且无料时 404
    if not material and not web and story_context is None:
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
    agent_attempted = False
    cross_language = _search_language(input_language) != output_search_language

    # ── 主路径：联网检索（短预算并行；agent 仅 enhance）──
    if web:
        relevance_names = poi_names_for(req.poi)
        expanded_names = _expanded_search_names(display_name, relevance_names)
        names_by_language = poi_names_by_language(req.poi)
        translated_questions = _fallback_query_translations(
            req.question, input_language
        )
        if len(translated_questions) < 3 and settings.guide_agent_enabled:
            translated_questions.update(
                guide_agent.translate_search_queries(
                    req.question,
                    input_language=input_language,
                )
            )
        translated_questions[_search_language(input_language)] = req.question

        language_order = list(
            dict.fromkeys(
                [
                    output_search_language,
                    _search_language(input_language),
                    "zh-CN",
                    "en",
                    "pt",
                ]
            )
        )
        query_sets: dict[str, list[str]] = {}
        for search_language in language_order:
            place_name = names_by_language.get(search_language) or display_name
            query_sets[search_language] = _web_search_queries(
                place_name,
                translated_questions.get(search_language, ""),
                aliases=relevance_names,
                language=search_language,
                limit=2,
            )
        raw_web_hits = [
            *(poi_official_hits_for(req.poi) if req.language.startswith("zh") else []),
            *_search_query_sets(query_sets, k=2, budget_s=3.5),
        ]
        web_hits = filter_relevant_hits(expanded_names, raw_web_hits)
        if _TEMPORAL_INTENT.search(req.question):
            web_hits = [
                hit
                for hit in web_hits
                if _TEMPORAL_FACT.search(str(hit.get("snippet") or ""))
            ]
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

            source_languages = {
                _search_language(str(hit.get("search_language") or req.language))
                for hit in web_hits
            }
            needs_synthesis = (
                enhance
                or story_context is not None
                or cross_language
                or req.language == "zh-TW"
                or any(language != output_search_language for language in source_languages)
            )
            if needs_synthesis:
                if settings.guide_agent_enabled:
                    agent_attempted = True
                    expl = guide_agent.answer(
                        display_name,
                        req.question,
                        material=combined,
                        language=req.language,
                        input_language=input_language,
                        interests=req.interests,
                        **answer_context,
                    )
                    if (
                        expl
                        and expl.text.strip()
                        and (story_context is not None or not _looks_like_refusal(expl.text))
                        and _guide_language_matches(expl, req.language)
                    ):
                        answer_text = expl.text
                        confidence = (
                            expl.confidence if story_context
                            else max(float(expl.confidence or 0.7), 0.7)
                        )
                        ai_generated = True
                        source = "agent+story+web" if story_context else "agent+web"
                    else:
                        has_target_web = any(
                            _search_language(str(hit.get("search_language") or ""))
                            == output_search_language
                            for hit in web_hits
                        )
                        language_safe_web = (
                            story_context is None
                            and not cross_language
                            and req.language != "zh-TW"
                            and has_target_web
                        )
                        if language_safe_web and not _looks_like_refusal(web_answer):
                            answer_text = web_answer
                            source = "web"
                            confidence = 0.65
                        if expl is None:
                            error = "guide agent unavailable; target-language fallback used"
                        elif _looks_like_refusal(expl.text):
                            error = "guide agent refused; target-language fallback used"
                        else:
                            error = "guide agent language mismatch; target-language fallback used"
                else:
                    error = "guide agent disabled; target-language fallback used"
            else:
                answer_text = web_answer
                source = "web"
                confidence = 0.65

    # ── 兜底：强相关本地摘录 / enhance 仅本地 / 空答案（不甩「手头没有」）──
    if not (answer_text or "").strip():
        if (
            (material.strip() or story_context is not None)
            and settings.guide_agent_enabled
            and (enhance or cross_language or story_context is not None)
            and not agent_attempted
        ):
            agent_attempted = True
            expl = guide_agent.answer(
                display_name,
                req.question,
                material=material,
                language=req.language,
                input_language=input_language,
                interests=req.interests,
                **answer_context,
            )
            if (
                expl
                and expl.text.strip()
                and (story_context is not None or not _looks_like_refusal(expl.text))
                and _guide_language_matches(expl, req.language)
            ):
                answer_text = expl.text
                confidence = (
                    expl.confidence if story_context
                    else max(float(expl.confidence or 0.7), 0.7)
                )
                ai_generated = True
                source = "agent+story" if story_context else "agent"

    if story_context is not None and not (answer_text or "").strip():
        answer_text = story_guide_fallback(story_context, language=req.language)
        source = "story"
        confidence = 0.5
        used_web = False
        web_hits = []
        error = "guide agent unavailable; served preset story notes"

    if not (answer_text or "").strip():
        if not weak and (local_answer or "").strip():
            answer_text = local_answer
            source = "rules"
            confidence = 0.55
            if (
                enhance and settings.guide_agent_enabled and material.strip()
                and not agent_attempted
            ):
                expl = guide_agent.answer(
                    display_name,
                    req.question,
                    material=material,
                    language=req.language,
                    input_language=input_language,
                    interests=req.interests,
                    **answer_context,
                )
                if (
                    expl
                    and expl.text.strip()
                    and not _looks_like_refusal(expl.text)
                    and _guide_language_matches(expl, req.language)
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
    if (
        story_context is None and source != "empty"
        and _looks_like_refusal(answer_text) and not used_web
    ):
        answer_text = _ASK_EMPTY.get(req.language, _ASK_EMPTY["zh-CN"])
        confidence = min(confidence, 0.3)
        source = "empty"

    if req.language in {"en", "pt"} and re.search(r"[\u3400-\u9fff]", answer_text):
        if story_context is not None:
            answer_text = story_guide_fallback(story_context, language=req.language)
            source = "story"
            ai_generated = False
            used_web = False
            web_hits = []
            confidence = 0.5
        elif local_answer and not re.search(r"[\u3400-\u9fff]", local_answer):
            answer_text = local_answer
            source = "rules"
            confidence = 0.55
        else:
            answer_text = _ASK_EMPTY[req.language]
            source = "empty"
            confidence = 0.25
        error = "language mismatch in upstream answer; served language-safe fallback"

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
            "input_language": input_language,
            "output_language": req.language,
            "story_context": story_context is not None,
            "history_turns": len(req.history),
        },
    )
    return {
        "poi_name": display_name,
        "question": req.question,
        "text": out_text,
        "language": req.language,
        "input_language": input_language,
        "source": source,
        "confidence": confidence,
        "ai_generated": ai_generated,
        "blocked": review.get("decision") == "block",
        "error": error,
        "review": review,
        "story_context_used": story_context is not None,
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
        travel_type=req.travel_type,
        next_distance=req.next_distance,
        next_walk_time=req.next_walk_time,
    )
    if preset is None:
        # 回退：旧 gather 路径仍找不到则 404
        poi_name, material = _gather_material(req.poi, req.poi)
        if not material:
            raise HTTPException(status_code=404, detail=f"找不到 POI 资料：{req.poi}")
        snippet = material.split("\n")[0][:500]
        preset = {
            "text": snippet,
            "audio_script": snippet,
            "immersive": {
                "title": poi_name or req.poi,
                "subtitle": "",
                "hook": snippet,
                "why_it_matters": "",
                "historical_story": "",
                "things_to_observe": [],
                "local_story": "",
                "interactive_suggestion": "",
                "next_exploration": {
                    "location": (req.next_stop or "").strip() if req.next_stop else "",
                    "distance": (req.next_distance or "").strip(),
                    "walk_time": (req.next_walk_time or "").strip(),
                    "reason": "",
                },
                "audio_script": snippet,
            },
            "sections": [
                {
                    "id": "overview",
                    "body": snippet,
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

    # 可选增强：guide agent 改写预设稿（优先结构化 immersive）
    poi_name, material = _gather_material(req.poi, req.poi)
    expl = guide_agent.generate(
        poi_name or str(preset.get("poi_name") or req.poi),
        material=material or str(preset.get("text") or ""),
        language=req.language,
        interests=req.interests,
        travel_type=req.travel_type,
        next_stop=req.next_stop,
    )
    if expl is not None and not _guide_language_matches(expl, req.language):
        logger.info("guide agent language mismatch; served language-safe preset")
        expl = None
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

    # Prefer agent immersive when it has real structure; else keep preset immersive.
    immersive = preset.get("immersive") or {}
    if expl.immersive is not None:
        agent_imm = expl.immersive.to_public_dict()
        rich = any(
            [
                agent_imm.get("why_it_matters"),
                agent_imm.get("historical_story"),
                agent_imm.get("things_to_observe"),
                agent_imm.get("local_story"),
            ]
        )
        if rich:
            # Preserve next-stop meta from request/preset when agent left blanks
            preset_next = (preset.get("immersive") or {}).get("next_exploration") or {}
            agent_next = agent_imm.get("next_exploration") or {}
            if not agent_next.get("location") and preset_next.get("location"):
                agent_next = {**preset_next, **{k: v for k, v in agent_next.items() if v}}
            for key in ("distance", "walk_time"):
                if not agent_next.get(key) and preset_next.get(key):
                    agent_next[key] = preset_next[key]
            agent_imm["next_exploration"] = agent_next
            if not agent_imm.get("title"):
                agent_imm["title"] = preset.get("poi_name") or req.poi
            if not agent_imm.get("audio_script"):
                agent_imm["audio_script"] = out_text
            immersive = agent_imm

    return {
        "text": out_text,
        "audio_script": (immersive or {}).get("audio_script") or out_text,
        "immersive": immersive,
        # Keep POI-field sections for pictorial UI when agent only rewrote TTS text.
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
    """Text-to-speech with fixed voices and OSS or development-local delivery."""
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


@router.get("/tts/audio/{filename}", response_model=bytes, response_class=FileResponse)
def tts_audio(filename: str) -> FileResponse:
    """Serve a temporary MP3 generated during local development."""
    path = local_audio_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Audio not found or expired")
    return FileResponse(
        path,
        media_type="audio/mpeg",
        filename="macau-storywalk-guide.mp3",
        headers={"Cache-Control": "private, max-age=3600"},
    )
