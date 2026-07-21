"""Ground postcard scenes on real POI visuals.

1. Build a fixed landmark brief from local POI fields (+ optional web notes).
2. Download a real reference photo (Openverse / Flickr) into
   ``harness/datasets/photos/poi_refs/{poi_id}.*``.
3. Cache the landmark brief under ``data/postcard_scenes/{poi_id}/_brief.json``.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.features.guide.web_search import search_web_multi
from app.features.postcards.scene_library import scenes_root

logger = logging.getLogger("macau_storywalk.scene_research")

_UA = "MacauStoryWalk/0.1 (competition; postcard-scenes; contact: local)"
_BRIEF_NAME = "_brief.json"
_REF_EXTS = (".jpg", ".jpeg", ".png", ".webp")


@dataclass
class SceneResearch:
    poi_id: str
    name_zh: str
    landmarks: str
    ref_image_path: str | None = None
    ref_image_url: str | None = None
    sources: list[str] = field(default_factory=list)
    wiki_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def photos_refs_root() -> Path:
    """Canonical store for web reference photos (phase 1)."""
    return settings.repo_root / "harness" / "datasets" / "photos" / "poi_refs"


def brief_path(poi_id: str) -> Path:
    return scenes_root() / poi_id / _BRIEF_NAME


def ref_image_candidates(poi_id: str) -> list[Path]:
    """Preferred harness path first; legacy postcard_scenes/_ref.* as fallback."""
    paths: list[Path] = []
    root = photos_refs_root()
    for ext in _REF_EXTS:
        paths.append(root / f"{poi_id}{ext}")
    legacy = scenes_root() / poi_id
    for ext in _REF_EXTS:
        paths.append(legacy / f"_ref{ext}")
    return paths


def load_cached_research(poi_id: str) -> SceneResearch | None:
    path = brief_path(poi_id)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict) or not raw.get("landmarks"):
        return None
    research = SceneResearch(
        poi_id=str(raw.get("poi_id") or poi_id),
        name_zh=str(raw.get("name_zh") or poi_id),
        landmarks=str(raw["landmarks"]),
        ref_image_path=raw.get("ref_image_path"),
        ref_image_url=raw.get("ref_image_url"),
        sources=list(raw.get("sources") or []),
        wiki_notes=str(raw.get("wiki_notes") or ""),
    )
    # Prefer an on-disk image even if path in JSON drifted.
    for candidate in ref_image_candidates(poi_id):
        if candidate.is_file():
            research.ref_image_path = str(candidate.resolve())
            break
    else:
        # Keep JSON path only if that file still exists.
        if research.ref_image_path and not Path(research.ref_image_path).is_file():
            research.ref_image_path = None
    return research


def save_research(research: SceneResearch) -> Path:
    path = brief_path(research.poi_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(research.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def local_landmarks(poi: dict[str, Any]) -> str:
    """Deterministic visual anchors from curated POI JSON (always available offline)."""
    bits: list[str] = []
    for key, label in (
        ("architecture", "建筑/街景"),
        ("observation_tips", "观察要点"),
        ("intro", "地点简介"),
    ):
        text = str(poi.get(key) or "").strip()
        if text:
            bits.append(f"- {label}：{text}")
    name = str(poi.get("name_zh") or poi.get("name_en") or poi.get("id") or "")
    district = str(poi.get("district") or "").strip()
    header = f"地点：{name}" + (f"（{district}）" if district else "")
    if not bits:
        return (
            f"{header}\n"
            "- 必须画澳门真实可辨识的街景/建筑，禁止随机几何块或无关动物。\n"
        )
    return header + "\n" + "\n".join(bits)


def research_queries(poi: dict[str, Any]) -> list[str]:
    name_zh = str(poi.get("name_zh") or "").strip()
    name_en = str(poi.get("name_en") or "").strip()
    name_pt = str(poi.get("name_pt") or "").strip()
    queries: list[str] = []
    if name_zh:
        queries.append(f"{name_zh} 澳门")
        queries.append(f"{name_zh} Macau")
    if name_en:
        queries.append(f"{name_en} Macau")
    if name_pt and name_pt not in queries:
        queries.append(f"{name_pt} Macau")
    return queries


def _wiki_summary(title: str, *, language: str) -> dict[str, Any] | None:
    lang = "zh" if language.startswith("zh") else ("pt" if language.startswith("pt") else "en")
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title, safe='')}"
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": _UA, "Accept": "application/json"},
            timeout=8.0,
            follow_redirects=True,
            trust_env=False,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        logger.info("wiki summary failed for %s: %s", title[:80], exc)
        return None


def _image_url_from_summary(summary: dict[str, Any]) -> str | None:
    for key in ("originalimage", "thumbnail"):
        block = summary.get(key)
        if isinstance(block, dict):
            src = str(block.get("source") or "").strip()
            if src.startswith("http"):
                return src
    return None


def _openverse_image(query: str) -> tuple[str | None, str | None]:
    """Search Openverse (CC Flickr/etc.) for a real photo of the place.

    Prefer non-Wikimedia hosts when possible — upload.wikimedia.org is often
    blocked (403) in this environment.
    """
    q = (query or "").strip()
    if not q:
        return None, None
    url = (
        "https://api.openverse.org/v1/images/"
        f"?q={quote(q)}&page_size=8&mature=false"
    )
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": _UA, "Accept": "application/json"},
            timeout=12.0,
            follow_redirects=True,
            trust_env=False,
        )
        if resp.status_code != 200:
            return None, None
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.info("openverse search failed: %s", exc)
        return None, None
    if not isinstance(data, dict):
        return None, None
    rows = [r for r in (data.get("results") or []) if isinstance(r, dict)]
    # Prefer Flickr/static hosts; defer wikimedia to last.
    preferred: list[dict] = []
    deferred: list[dict] = []
    for row in rows:
        image_url = str(row.get("url") or "").strip()
        if not image_url.startswith("http"):
            continue
        if "wikimedia.org" in image_url or "wikipedia.org" in image_url:
            deferred.append(row)
        else:
            preferred.append(row)
    for row in preferred + deferred:
        image_url = str(row.get("url") or "").strip()
        landing = str(row.get("foreign_landing_url") or row.get("detail_url") or "").strip()
        return image_url, landing or image_url
    return None, None


def find_reference_image(
    poi: dict[str, Any],
    *,
    hits: list[dict[str, str]] | None = None,
) -> tuple[str | None, str | None]:
    """Return ``(image_url, source_page_url)``.

    Prefer Openverse (works without Wikimedia bot unblock). Fall back to
    Wikipedia page lead images when available.
    """
    queries: list[str] = []
    name_zh = str(poi.get("name_zh") or "").strip()
    name_en = str(poi.get("name_en") or "").strip()
    name_pt = str(poi.get("name_pt") or "").strip()
    if name_en:
        queries.append(f"{name_en} Macau")
    if name_zh:
        queries.append(f"{name_zh} 澳门")
        queries.append(f"{name_zh} Macau")
    if name_pt:
        queries.append(f"{name_pt} Macau")
    for q in queries:
        image_url, page = _openverse_image(q)
        if image_url:
            return image_url, page

    titles: list[str] = []
    for hit in hits or []:
        title = str(hit.get("title") or "").strip()
        source = str(hit.get("source") or "")
        if title and source.startswith("wikipedia"):
            titles.append(title)
    for name in (name_zh, name_en, name_pt):
        if name and name not in titles:
            titles.append(name)

    for title in titles[:6]:
        for lang in ("zh-CN", "en", "pt"):
            summary = _wiki_summary(title, language=lang)
            if not summary or summary.get("type") == "disambiguation":
                continue
            image_url = _image_url_from_summary(summary)
            if not image_url:
                continue
            page = (
                (summary.get("content_urls") or {})
                .get("desktop", {})
                .get("page")
            )
            return image_url, str(page or summary.get("title") or title)
    return None, None


def download_reference_image(poi_id: str, image_url: str) -> Path | None:
    try:
        resp = httpx.get(
            image_url,
            headers={"User-Agent": _UA},
            timeout=20.0,
            follow_redirects=True,
            trust_env=False,
        )
        if resp.status_code != 200 or not resp.content:
            return None
        ctype = (resp.headers.get("content-type") or "").lower()
        if "png" in ctype:
            ext = ".png"
        elif "webp" in ctype:
            ext = ".webp"
        else:
            ext = ".jpg"
        # Clear older refs (harness + legacy postcard_scenes paths)
        for old in ref_image_candidates(poi_id):
            try:
                old.unlink()
            except FileNotFoundError:
                pass
        dest = photos_refs_root() / f"{poi_id}{ext}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return dest
    except Exception as exc:  # noqa: BLE001
        logger.info("ref image download failed: %s", exc)
        return None


def research_poi(
    poi: dict[str, Any],
    *,
    force: bool = False,
    use_web: bool = True,
    budget_s: float = 8.0,
) -> SceneResearch:
    """Research once per POI. Cached under ``_brief.json`` + ``_ref.*``."""
    poi_id = str(poi.get("id") or "").strip()
    if not poi_id:
        raise ValueError("poi missing id")

    if not force:
        cached = load_cached_research(poi_id)
        # Reuse brief when we already have a reference photo on disk.
        if cached and cached.landmarks and cached.ref_image_path:
            return cached
        # Brief without photo: continue below to retry Openverse download.
        if cached and cached.landmarks and not use_web:
            return cached

    name_zh = str(poi.get("name_zh") or poi.get("name_en") or poi_id)
    landmarks = local_landmarks(poi)
    sources: list[str] = ["pois.json"]
    wiki_notes = ""
    ref_url: str | None = None
    ref_path: str | None = None
    hits: list[dict[str, str]] = []

    if use_web:
        try:
            hits = search_web_multi(
                research_queries(poi),
                language="zh-CN",
                k=3,
                max_queries=3,
                budget_s=budget_s,
            )
        except Exception as exc:  # noqa: BLE001
            logger.info("scene research web search skipped: %s", exc)
            hits = []

        snippets: list[str] = []
        for hit in hits[:3]:
            snip = re.sub(r"\s+", " ", str(hit.get("snippet") or "")).strip()
            if snip:
                snippets.append(f"- {hit.get('title', '')}: {snip[:280]}")
            if hit.get("url"):
                sources.append(str(hit["url"]))
        if snippets:
            wiki_notes = "\n".join(snippets)
            landmarks = (
                landmarks
                + "\n联网补充（仅用于核对真实外观，勿画无关物体）：\n"
                + wiki_notes
            )

        ref_url, page = find_reference_image(poi, hits=hits)
        if ref_url:
            saved = download_reference_image(poi_id, ref_url)
            if saved:
                ref_path = str(saved.resolve())
                sources.append(ref_url)
                if page:
                    sources.append(page)

    # Deduplicate sources while preserving order
    seen: set[str] = set()
    uniq_sources: list[str] = []
    for src in sources:
        if src and src not in seen:
            seen.add(src)
            uniq_sources.append(src)

    research = SceneResearch(
        poi_id=poi_id,
        name_zh=name_zh,
        landmarks=landmarks.strip(),
        ref_image_path=ref_path,
        ref_image_url=ref_url,
        sources=uniq_sources,
        wiki_notes=wiki_notes,
    )
    save_research(research)
    return research
