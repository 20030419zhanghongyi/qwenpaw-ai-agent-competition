"""Theme-first day allocation and POI-pool day shells.

Primary route path for ``match_routes``: build days from POI pools by theme /
interest. Preset templates are deprecated and used only as emergency fallback.

When selected themes outnumber trip days, themes are partitioned across days
(balanced sizes); any day with 2+ themes builds a mixed POI itinerary.
Empty themes/interests default to heritage.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.user import Preference, TRIP_DAYS_DEFAULT, clamp_trip_days

from .poi_metadata import get_poi_metadata, list_poi_metadata

# UI theme order when days < number of selected themes.
_THEME_PRIORITY = (
    "cotai",
    "heritage",
    "food",
    "architecture",
    "photo",
    "leisure",
    "family",
)

_THEME_LABELS = {
    "cotai": "路氹度假区",
    "heritage": "历史城区",
    "food": "美食街巷",
    "architecture": "建筑风貌",
    "photo": "摄影打卡",
    "leisure": "休闲漫步",
    "family": "亲子友好",
}

# Interest tags → synthetic theme when themes list is empty.
_INTEREST_TO_THEME = {
    "history": "heritage",
    "culture": "heritage",
    "food": "food",
    "architecture": "architecture",
    "photo": "photo",
}

_PENINSULA_HERITAGE = frozenset(
    {"大堂区", "风顺堂区", "望德堂区", "花王堂区", "花地玛堂区"}
)
_COTAI_DISTRICTS = frozenset({"路氹填海区", "嘉模堂区"})

# Seed landmarks per theme (ordered preference).
_THEME_SEEDS: dict[str, tuple[str, ...]] = {
    "cotai": ("poi_0020", "poi_0021", "poi_0107", "poi_0012", "poi_0109"),
    "cotai_west": ("poi_0020", "poi_0021", "poi_0107", "poi_0012", "poi_0008"),
    "cotai_east": ("poi_0109", "poi_0027", "poi_0110", "poi_0230", "poi_0112"),
    "heritage": ("poi_0001", "poi_0002", "poi_0011", "poi_0003", "poi_0004"),
    "heritage_south": ("poi_0011", "poi_0002", "poi_0001", "poi_0005"),
    "heritage_north": ("poi_0001", "poi_0003", "poi_0004", "poi_0006"),
    "food": ("poi_0004", "poi_0016", "poi_0080", "poi_0096", "poi_0046", "poi_0002"),
    "architecture": ("poi_0001", "poi_0109", "poi_0020", "poi_0002"),
    "photo": ("poi_0001", "poi_0020", "poi_0021", "poi_0012"),
    "leisure": ("poi_0012", "poi_0008", "poi_0098"),
    "family": ("poi_0012", "poi_0008", "poi_0110"),
}

_THEME_SUITABLE: dict[str, frozenset[str]] = {
    "cotai": frozenset({"photo", "architecture", "relax", "culture"}),
    "cotai_west": frozenset({"photo", "architecture", "relax", "culture"}),
    "cotai_east": frozenset({"photo", "architecture", "relax", "culture"}),
    "heritage": frozenset({"history", "culture", "architecture", "photo"}),
    "heritage_south": frozenset({"history", "culture", "architecture", "photo"}),
    "heritage_north": frozenset({"history", "culture", "architecture", "photo"}),
    "food": frozenset({"food"}),
    "architecture": frozenset({"architecture", "photo", "culture"}),
    "photo": frozenset({"photo", "architecture"}),
    "leisure": frozenset({"relax", "photo", "culture"}),
    "family": frozenset({"family", "relax", "photo"}),
}


@dataclass(frozen=True)
class DaySpec:
    theme_key: str
    label: str
    base_theme: str
    # When set, one day interleaves POIs from all listed base themes.
    mix_themes: tuple[str, ...] = ()


def should_use_theme_days(pref: Preference) -> bool:
    """Always prefer POI-pool theme days; preset templates are deprecated."""
    return True


def _normalize_themes(pref: Preference) -> list[str]:
    themes = [t for t in (pref.themes or []) if t in _THEME_PRIORITY]
    if themes:
        seen: list[str] = []
        for tag in themes:
            if tag not in seen:
                seen.append(tag)
        return seen
    inferred: list[str] = []
    for interest in pref.interests or []:
        mapped = _INTEREST_TO_THEME.get(interest)
        if mapped and mapped not in inferred:
            inferred.append(mapped)
    return inferred or ["heritage"]


def _day_count(pref: Preference) -> int:
    if pref.duration == "multi-day":
        return clamp_trip_days(pref.trip_days) or TRIP_DAYS_DEFAULT
    return 1


def _subcorridor(base: str, occurrence: int) -> str:
    """When the same base theme spans multiple days, alternate sub-corridors."""
    if occurrence <= 0:
        return base
    if base == "cotai":
        return "cotai_east" if occurrence % 2 else "cotai_west"
    if base == "heritage":
        return "heritage_north" if occurrence % 2 else "heritage_south"
    return base


def _partition_themes(ranked: list[str], n_days: int) -> list[list[str]]:
    """Split themes into ``n_days`` groups with sizes differing by at most one.

    Extra themes go to earlier days (priority-ranked order preserved).
    Example: 3 themes / 2 days → [[a, b], [c]]; 4 / 2 → [[a, b], [c, d]].
    """
    n = len(ranked)
    if n_days <= 0:
        return [list(ranked)] if ranked else []
    if n == 0:
        return [[] for _ in range(n_days)]
    base, rem = divmod(n, n_days)
    sizes = [base + (1 if i < rem else 0) for i in range(n_days)]
    groups: list[list[str]] = []
    index = 0
    for size in sizes:
        groups.append(ranked[index : index + size])
        index += size
    return groups


def _spec_for_single_theme(raw: str, base_counts: dict[str, int]) -> DaySpec:
    if raw.startswith("cotai_") or raw.startswith("heritage_"):
        base = "cotai" if raw.startswith("cotai") else "heritage"
        key = raw
        base_counts[base] = base_counts.get(base, 0) + 1
    else:
        base = raw
        count = base_counts.get(base, 0)
        key = _subcorridor(base, count) if count else base
        base_counts[base] = count + 1
    label = _THEME_LABELS.get(base, base)
    if key != base and ("east" in key or "north" in key or "west" in key or "south" in key):
        label = f"{label}（另一走廊）"
    return DaySpec(theme_key=key, label=label, base_theme=base)


def _spec_for_theme_group(group: list[str], base_counts: dict[str, int]) -> DaySpec:
    """One theme → corridor DaySpec; several themes → mixed DaySpec."""
    if len(group) == 1:
        return _spec_for_single_theme(group[0], base_counts)
    labels = [_THEME_LABELS.get(tag, tag) for tag in group]
    return DaySpec(
        theme_key="mixed",
        label=" · ".join(labels),
        base_theme="mixed",
        mix_themes=tuple(group),
    )


def allocate_theme_days(pref: Preference) -> list[DaySpec]:
    """Map preference themes onto itinerary days.

    - themes == days: one theme per day
    - themes < days: repeat primary theme via sub-corridors
    - themes > days: balanced partition; days with 2+ themes build mixed itineraries
    """
    themes = _normalize_themes(pref)
    n_days = _day_count(pref)

    ranked = sorted(
        themes,
        key=lambda tag: (
            _THEME_PRIORITY.index(tag) if tag in _THEME_PRIORITY else 99,
            themes.index(tag),
        ),
    )

    base_counts: dict[str, int] = {}

    # More themes than days → pack multiple themes onto some days.
    if len(ranked) > n_days:
        return [
            _spec_for_theme_group(group, base_counts)
            for group in _partition_themes(ranked, n_days)
            if group
        ]

    if len(ranked) == n_days:
        return [_spec_for_single_theme(tag, base_counts) for tag in ranked]

    # Fewer themes than days → fill remaining days with primary sub-corridors.
    chosen = list(ranked)
    primary = ranked[0]
    occ = 0
    while len(chosen) < n_days:
        occ += 1
        chosen.append(_subcorridor(primary, occ))
    return [_spec_for_single_theme(raw, base_counts) for raw in chosen]


def _districts_for(theme_key: str) -> frozenset[str] | None:
    if theme_key.startswith("cotai"):
        return _COTAI_DISTRICTS
    if theme_key == "food":
        return _PENINSULA_HERITAGE | frozenset({"嘉模堂区"})
    if theme_key in {"leisure", "family"}:
        return _PENINSULA_HERITAGE | _COTAI_DISTRICTS
    if theme_key.startswith("heritage") or theme_key in {"architecture", "photo"}:
        return _PENINSULA_HERITAGE
    return None


def _score_poi_for_theme(poi: dict, theme_key: str) -> int:
    tags = set(poi.get("suitable_for") or [])
    base = theme_key.split("_")[0]
    wanted = _THEME_SUITABLE.get(theme_key) or _THEME_SUITABLE.get(base, frozenset())
    if not wanted:
        return 0
    overlap = tags & wanted
    if not overlap:
        return 0
    score = len(overlap) * 3
    districts = _districts_for(theme_key)
    if districts and str(poi.get("district") or "") in districts:
        score += 4
    if theme_key.startswith("cotai") and str(poi.get("district") or "") in _COTAI_DISTRICTS:
        score += 3
    if theme_key == "food" and "food" in tags:
        score += 2
    if theme_key.startswith("heritage") and ("history" in tags or "culture" in tags):
        score += 2
    return score


def select_pois_for_theme(theme_key: str, *, limit: int = 12) -> list[str]:
    """Rank POIs for a theme corridor; seeds first, then scored pool."""
    seeds = [pid for pid in _THEME_SEEDS.get(theme_key, ()) if get_poi_metadata(pid)]
    if not seeds:
        base = theme_key.split("_")[0]
        seeds = [pid for pid in _THEME_SEEDS.get(base, ()) if get_poi_metadata(pid)]

    scored: list[tuple[int, str]] = []
    seed_set = set(seeds)
    for poi in list_poi_metadata():
        poi_id = str(poi.get("id") or "")
        if not poi_id or poi_id in seed_set:
            continue
        if poi_id.startswith("poi_port_"):
            continue
        score = _score_poi_for_theme(poi, theme_key)
        if score <= 0:
            continue
        districts = _districts_for(theme_key)
        if districts and str(poi.get("district") or "") not in districts:
            continue
        scored.append((score, poi_id))
    scored.sort(key=lambda item: (-item[0], item[1]))

    ordered = list(seeds)
    for _, poi_id in scored:
        if poi_id not in ordered:
            ordered.append(poi_id)
        if len(ordered) >= limit:
            break
    return ordered[:limit]


def select_pois_for_themes(theme_keys: list[str], *, limit: int = 12) -> list[str]:
    """Round-robin POIs across themes for balanced single-day coverage."""
    if not theme_keys:
        return []
    if len(theme_keys) == 1:
        return select_pois_for_theme(theme_keys[0], limit=limit)

    # Pull enough from each theme so interleaving can still fill the day.
    per_theme = max(3, (limit + len(theme_keys) - 1) // len(theme_keys) + 1)
    pools = [select_pois_for_theme(key, limit=per_theme) for key in theme_keys]

    ordered: list[str] = []
    seen: set[str] = set()
    max_len = max((len(pool) for pool in pools), default=0)
    for index in range(max_len):
        for pool in pools:
            if index >= len(pool):
                continue
            poi_id = pool[index]
            if poi_id in seen:
                continue
            ordered.append(poi_id)
            seen.add(poi_id)
            if len(ordered) >= limit:
                return ordered
    return ordered[:limit]


def build_theme_day_shell(spec: DaySpec, pref: Preference) -> dict:
    """Build a lightweight route shell for ``construct_route`` (not a preset)."""
    limit = 6 if pref.duration == "evening" else 12
    mix = list(spec.mix_themes) if spec.mix_themes else []
    if mix:
        poi_ids = select_pois_for_themes(mix, limit=limit)
    else:
        poi_ids = select_pois_for_theme(spec.theme_key, limit=limit)
    if not poi_ids:
        poi_ids = ["poi_0001", "poi_0002"]

    # Mixed days: seed from the first stop of each theme when possible.
    if mix and len(mix) >= 2:
        seed_ids: list[str] = []
        seen_seeds: set[str] = set()
        for theme_key in mix:
            for pid in select_pois_for_theme(theme_key, limit=2):
                if pid in seen_seeds:
                    continue
                seed_ids.append(pid)
                seen_seeds.add(pid)
                break
            if len(seed_ids) >= 2:
                break
        if len(seed_ids) < 2:
            for pid in poi_ids:
                if pid not in seen_seeds:
                    seed_ids.append(pid)
                    seen_seeds.add(pid)
                if len(seed_ids) >= 2:
                    break
    else:
        seed_ids = poi_ids[:2]

    nodes = []
    for index, poi_id in enumerate(seed_ids, start=1):
        nodes.append(
            {
                "poi_id": poi_id,
                "order": index,
                "suggested_stay_min": 35,
                "note": f"主题日种子 · {spec.label}",
                "replaceable_with": [],
            }
        )

    hours = {
        "half-day": 3.0,
        "evening": 2.0,
        "full-day": 3.5,
        "multi-day": 3.5,
    }.get(pref.duration or "full-day", 3.5)
    full_day = pref.duration in {"multi-day", "full-day"}
    suitable: list[str] = []
    if mix:
        for key in mix:
            for tag in _THEME_SUITABLE.get(key, ()):
                if tag not in suitable:
                    suitable.append(tag)
    else:
        suitable = list(_THEME_SUITABLE.get(spec.theme_key, ()) or [])

    shell_id = (
        f"theme_day_mixed_{'_'.join(mix)}" if mix else f"theme_day_{spec.theme_key}"
    )
    description = (
        f"按偏好主题「{spec.label}」混合生成一日行程，非预设模板。"
        if mix
        else f"按偏好主题「{spec.label}」从景点池生成，非预设模板。"
    )
    return {
        "id": shell_id,
        "name": f"{spec.label}主题日",
        "theme": spec.label,
        "duration_label": "一日" if full_day else "半日",
        "duration_hours": hours,
        "walk_distance_km": 1.2,
        "physical_level": "low" if "less-walk" in (pref.physical or []) else "medium",
        "suitable_for": suitable,
        "nodes": nodes,
        "description": description,
        "candidate_pool_ids": poi_ids,
        "theme_key": spec.theme_key,
        "base_theme": spec.base_theme,
        "mix_themes": mix,
    }


def build_candidate_pool_for_shell(shell: dict) -> list[dict]:
    """Minimal candidate pool so construct_route interest-insert can run."""
    pool_ids = list(shell.get("candidate_pool_ids") or [])
    nodes = shell.get("nodes") or []
    if not nodes:
        return []
    source = nodes[0]["poi_id"]
    candidates = [
        {"poi_id": poi_id, "score": 5, "reasons": ["主题日候选"]}
        for poi_id in pool_ids
        if poi_id != source
    ]
    return [{"source_poi_id": source, "candidates": candidates}]
