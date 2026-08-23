"""轻量联网检索：维基百科 + DuckDuckGo Instant Answer（无需 API key）。

用于 /guide/ask 在本地 POI 资料不够时补充公开百科信息。
失败一律返回空列表，由调用方降级，不抛穿。

延迟约束：单请求短超时 + 总预算（默认 2.5s）+ 查询并行，避免多查询串行拖垮 UX。
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("macau_storywalk.web_search")

_UA = "MacauStoryWalk/0.1 (competition; guide-ask; contact: local)"
# 单次 HTTP：短超时，宁可 miss 也不拖垮 ask
_TIMEOUT = 2.0
# 整次 search_web_multi 墙钟预算（秒）
_DEFAULT_BUDGET_S = 2.5
_MAX_WORKERS = 4
_GENERIC_PLACE_WORDS = {
    "a",
    "da",
    "de",
    "do",
    "dos",
    "macao",
    "macau",
    "museum",
    "museu",
    "church",
    "igreja",
    "temple",
    "templo",
    "square",
    "praca",
    "garden",
    "jardim",
    "street",
    "rua",
    "place",
    "centre",
    "center",
    "cultural",
    "cultura",
    "hotel",
    "beach",
    "praia",
}


def _wiki_lang(language: str) -> str:
    if language.startswith("zh"):
        return "zh"
    if language.startswith("pt"):
        return "pt"
    return "en"


def _get_json(url: str, *, timeout: float = _TIMEOUT) -> Any | None:
    try:
        # trust_env=False：避免继承坏掉的 HTTP(S)_PROXY 导致检索静默全失败
        resp = httpx.get(
            url,
            headers={"User-Agent": _UA, "Accept": "application/json"},
            timeout=timeout,
            follow_redirects=True,
            trust_env=False,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.info("web_search GET 失败：%s (%s)", url[:120], exc)
        return None


def _strip_html(raw: str) -> str:
    return re.sub(r"<[^>]+>", "", raw or "").strip()


def _normalize_relevance_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = text.replace("macao", "macau").replace("saint", "st")
    return " ".join(re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+", text))


def filter_relevant_hits(
    poi_names: str | list[str],
    hits: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Keep only results anchored to the requested POI, never merely its category."""
    names = [poi_names] if isinstance(poi_names, str) else poi_names
    names = [name for name in names if _normalize_relevance_text(name)]
    if not names:
        return []

    def matches(name: str, haystack: str) -> bool:
        normalized_name = _normalize_relevance_text(name)
        if re.search(r"[\u3400-\u9fff]", name or "") is not None:
            return normalized_name in haystack
        distinctive = [
            token
            for token in normalized_name.split()
            if token not in _GENERIC_PLACE_WORDS and len(token) >= 3
        ]
        phrase_match = normalized_name in haystack
        token_matches = sum(token in haystack.split() for token in distinctive)
        required = max(1, (2 * len(distinctive) + 2) // 3)
        return phrase_match or bool(distinctive and token_matches >= required)

    relevant: list[dict[str, str]] = []
    for hit in hits:
        haystack = _normalize_relevance_text(
            f"{hit.get('title') or ''} {hit.get('snippet') or ''}"
        )
        if not haystack:
            continue
        if any(matches(name, haystack) for name in names):
            relevant.append(hit)
    return relevant


def _wikipedia_hits(
    query: str,
    *,
    language: str,
    k: int,
    fetch_summary: bool = True,
) -> list[dict[str, str]]:
    """维基检索。默认只取首条摘要（1 次额外 HTTP）；其余用 search snippet，省延迟。"""
    lang = _wiki_lang(language)
    search_url = (
        f"https://{lang}.wikipedia.org/w/api.php"
        f"?action=query&list=search&srsearch={quote(query)}"
        f"&srlimit={k}&format=json&utf8=1"
    )
    data = _get_json(search_url)
    if not isinstance(data, dict):
        if lang != "en":
            return _wikipedia_hits(query, language="en", k=k, fetch_summary=fetch_summary)
        return []

    rows = list((data.get("query") or {}).get("search") or [])
    hits: list[dict[str, str]] = []
    for i, row in enumerate(rows):
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        page_url = f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
        extract = _strip_html(str(row.get("snippet") or ""))
        # 仅首条拉完整 summary；其余用 search snippet，避免 k 次串行 HTTP
        if fetch_summary and i == 0:
            summary_url = (
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
                f"{quote(title, safe='')}"
            )
            summary = _get_json(summary_url)
            if isinstance(summary, dict):
                extract = str(summary.get("extract") or extract).strip()
                page_url = str(
                    summary.get("content_urls", {})
                    .get("desktop", {})
                    .get("page")
                    or page_url
                )
        if extract:
            hits.append(
                {
                    "title": title,
                    "snippet": extract[:600],
                    "url": page_url,
                    "source": f"wikipedia:{lang}",
                }
            )
        if len(hits) >= k:
            break
    return hits


def _duckduckgo_hit(query: str) -> list[dict[str, str]]:
    url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1&skip_disambig=1"
    data = _get_json(url)
    if not isinstance(data, dict):
        return []
    abstract = str(data.get("AbstractText") or "").strip()
    heading = str(data.get("Heading") or query).strip()
    abs_url = str(data.get("AbstractURL") or "").strip()
    hits: list[dict[str, str]] = []
    if abstract:
        hits.append(
            {
                "title": heading,
                "snippet": abstract[:600],
                "url": abs_url or "https://duckduckgo.com/",
                "source": "duckduckgo",
            }
        )
    for topic in (data.get("RelatedTopics") or [])[:2]:
        if not isinstance(topic, dict):
            continue
        text = str(topic.get("Text") or "").strip()
        first_url = str(topic.get("FirstURL") or "").strip()
        if text and first_url:
            hits.append(
                {
                    "title": text.split(" - ")[0][:80],
                    "snippet": text[:400],
                    "url": first_url,
                    "source": "duckduckgo",
                }
            )
    return hits[:3]


def search_web(query: str, *, language: str = "zh-CN", k: int = 3) -> list[dict[str, str]]:
    """返回 [{title, snippet, url, source}, ...]。Wiki + DDG 并行。"""
    q = (query or "").strip()
    if not q:
        return []
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    wiki_hits: list[dict[str, str]] = []
    ddg_hits: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_wiki = pool.submit(_wikipedia_hits, q, language=language, k=k)
        fut_ddg = pool.submit(_duckduckgo_hit, q)
        try:
            wiki_hits = fut_wiki.result()
        except Exception as exc:  # noqa: BLE001
            logger.info("wikipedia 并行失败：%s", exc)
        try:
            ddg_hits = fut_ddg.result()
        except Exception as exc:  # noqa: BLE001
            logger.info("duckduckgo 并行失败：%s", exc)

    for hit in wiki_hits + ddg_hits:
        key = hit.get("url") or hit.get("title") or ""
        if not key or key in seen:
            continue
        seen.add(key)
        results.append(hit)
        if len(results) >= k:
            break
    return results


def _merge_hits(
    hits: list[dict[str, str]],
    *,
    seen: set[str],
    results: list[dict[str, str]],
    k: int,
) -> bool:
    """合并命中；满 k 返回 True。"""
    for hit in hits:
        key = hit.get("url") or hit.get("title") or ""
        if not key or key in seen:
            continue
        seen.add(key)
        results.append(hit)
        if len(results) >= k:
            return True
    return False


def search_web_multi(
    queries: list[str],
    *,
    language: str = "zh-CN",
    k: int = 3,
    max_queries: int = 2,
    budget_s: float = _DEFAULT_BUDGET_S,
) -> list[dict[str, str]]:
    """多查询并行检索并去重；受总预算约束，超时即返回已有结果。

    - 最多 ``max_queries`` 条（默认 2）
    - 墙钟 ``budget_s``（默认 2.5s）用尽即停
    - 中文查询仅在首轮无结果时再试英文维基（避免每条双倍串行）
    """
    cleaned: list[str] = []
    seen_q: set[str] = set()
    for raw in queries:
        q = (raw or "").strip()
        if not q or q in seen_q:
            continue
        seen_q.add(q)
        cleaned.append(q)
        if len(cleaned) >= max_queries:
            break
    if not cleaned:
        return []

    t0 = time.perf_counter()
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    def _one(q: str, lang: str) -> list[dict[str, str]]:
        remaining = budget_s - (time.perf_counter() - t0)
        if remaining <= 0.05:
            return []
        return search_web(q, language=lang, k=k)

    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(cleaned))) as pool:
        futs = {pool.submit(_one, q, language): q for q in cleaned}
        try:
            for fut in as_completed(futs, timeout=max(0.05, budget_s)):
                if time.perf_counter() - t0 >= budget_s:
                    break
                try:
                    hits = fut.result()
                except Exception as exc:  # noqa: BLE001
                    logger.info("search_web_multi 查询失败：%s", exc)
                    continue
                if _merge_hits(hits, seen=seen, results=results, k=k):
                    return results
        except TimeoutError:
            logger.info("search_web_multi 预算用尽（%.1fs）", budget_s)

    # 首轮无结果且中文：预算内再试英文（单查询，失败快）
    if (
        not results
        and language.startswith("zh")
        and time.perf_counter() - t0 < budget_s
    ):
        remaining = budget_s - (time.perf_counter() - t0)
        if remaining > 0.2:
            hits = search_web(cleaned[0], language="en", k=k)
            _merge_hits(hits, seen=seen, results=results, k=k)

    return results


def format_web_material(hits: list[dict[str, str]], *, language: str) -> str:
    if not hits:
        return ""
    header = {
        "zh-CN": "联网公开资料（仅作补充，需标明来源，不可编造）：",
        "zh-TW": "聯網公開資料（僅作補充，需標明來源，不可編造）：",
        "en": "Public web notes (supplement only; cite sources; do not invent):",
        "pt": "Notas públicas da web (apenas suplemento; cite fontes; não invente):",
    }.get(language, "联网公开资料（仅作补充，需标明来源，不可编造）：")
    blocks = [header]
    for i, hit in enumerate(hits, 1):
        blocks.append(
            f"[{i}] {hit.get('title', '')}（{hit.get('source', 'web')}）\n"
            f"{hit.get('snippet', '')}\n"
            f"来源：{hit.get('url', '')}"
        )
    return "\n\n".join(blocks)
