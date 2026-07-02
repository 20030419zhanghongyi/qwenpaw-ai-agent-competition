"""路线解释层。

把模板命中理由、约束应用说明和候选点信息统一整理为
适合前端直接展示的 explanation block。
"""

from __future__ import annotations


def build_explanation(
    *,
    template_id: str,
    reasons: list[str],
    applied_constraints: list[str],
    candidate_pois: list[dict],
) -> dict:
    """构造统一解释结构。"""
    return {
        "summary": _dedupe(reasons),
        "selected_template": template_id,
        "constraints": _dedupe(applied_constraints),
        "candidate_overview": _candidate_overview(candidate_pois),
    }


def _candidate_overview(candidate_pois: list[dict]) -> list[dict]:
    overview: list[dict] = []
    for entry in candidate_pois:
        top = entry.get("candidates", [])[:2]
        overview.append(
            {
                "source_poi_id": entry.get("source_poi_id"),
                "top_candidates": [
                    {
                        "poi_id": item["poi_id"],
                        "reasons": item["reasons"][:2],
                    }
                    for item in top
                ],
            }
        )
    return overview


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))

