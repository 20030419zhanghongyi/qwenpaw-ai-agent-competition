"""轻量联网检索：维基百科 + DuckDuckGo Instant Answer（无需 API key）。

用于 /guide/ask 在本地 POI 资料不够时补充公开百科信息。
失败一律返回空列表，由调用方降级，不抛穿。
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("macau_storywalk.web_search")

_UA = "MacauStoryWalk/0.1 (competition; guide-ask; contact: local)"
_TIMEOUT = 8.0


def _wiki_lang(language: str) -> str:
    if language.startswith("zh"):
        return "zh"
    if language.startswith("pt"):
        return "pt"
    return "en"


def _get_json(url: str) -> Any | None:
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": _UA, "Accept": "application/json"},
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.info("web_search GET 失败：%s (%s)", url[:120], exc)
        return None


def _wikipedia_hits(query: str, *, language: str, k: int) -> list[dict[str, str]]:
    lang = _wiki_lang(language)
    search_url = (
        f"https://{lang}.wikipedia.org/w/api.php"
        f"?action=query&list=search&srsearch={quote(query)}"
        f"&srlimit={k}&format=json&utf8=1"
    )
    data = _get_json(search_url)
    if not isinstance(data, dict):
        # 简中失败时试英文
        if lang != "en":
            return _wikipedia_hits(query, language="en", k=k)
        return []

    hits: list[dict[str, str]] = []
    for row in (data.get("query") or {}).get("search") or []:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        summary_url = (
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}"
        )
        summary = _get_json(summary_url)
        extract = ""
        page_url = f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
        if isinstance(summary, dict):
            extract = str(summary.get("extract") or "").strip()
            page_url = str(summary.get("content_urls", {}).get("desktop", {}).get("page") or page_url)
        if not extract:
            # fallback: strip HTML from search snippet
            raw = str(row.get("snippet") or "")
            extract = re.sub(r"<[^>]+>", "", raw).strip()
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
    for topic in (data.get("RelatedTopics") or [])[:3]:
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
    """返回 [{title, snippet, url, source}, ...]。"""
    q = (query or "").strip()
    if not q:
        return []
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    for hit in _wikipedia_hits(q, language=language, k=k) + _duckduckgo_hit(q):
        key = hit.get("url") or hit.get("title") or ""
        if not key or key in seen:
            continue
        seen.add(key)
        results.append(hit)
        if len(results) >= k:
            break
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
