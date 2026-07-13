"""规则项打分（见 harness/rubrics/rule_checks.md）。

纯函数：给定一条 case 和 agent/路线输出，返回 {checks, score}。
无网络、无 LLM，可单测。case 分 = 通过项 / 总项；run 分 = case 分均值。
"""

from __future__ import annotations

from typing import Any

from app.db.data import get_poi


def _has_keyword(text: str, keywords: list[str]) -> bool:
    """任一关键词（不区分大小写、不做分词）出现在文本里。"""
    hay = (text or "").lower()
    return any(k.lower() in hay for k in keywords)


def _route_blob(resp: dict[str, Any]) -> str:
    """把路线响应里所有「解释性文本」拼成一团，供关键词核对。"""
    parts = [
        resp.get("applied_constraints"),
        resp.get("rationale"),
        (resp.get("explanation") or {}).get("summary"),
    ]
    return " ".join(str(p) for p in parts if p)


def score_route_case(case: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
    """对 /routes/adjust 响应打分。expect 键见 rule_checks.md。"""
    exp = case.get("expect", {})
    pref_after = resp.get("preference_after", {}) or {}
    added = resp.get("added_nodes", []) or []
    removed = resp.get("removed_nodes", []) or []
    blob = _route_blob(resp)

    checks: list[tuple[str, bool]] = []

    if "physical" in exp:
        have = set(pref_after.get("physical", []))
        checks.append(("physical", all(t in have for t in exp["physical"])))

    if "interests" in exp:
        have = set(pref_after.get("interests", []))
        checks.append(("interests", all(t in have for t in exp["interests"])))

    if "duration" in exp:
        checks.append(("duration", pref_after.get("duration") == exp["duration"]))

    if "added_tag" in exp:
        tag = exp["added_tag"]
        hit = False
        for node in added:
            poi = get_poi(node.get("poi_id")) if node.get("poi_id") else None
            if poi and tag in poi.get("suitable_for", []):
                hit = True
                break
        checks.append((f"added_tag:{tag}", hit))

    if exp.get("removed_tail"):
        checks.append(("removed_tail", len(removed) > 0))

    if "keywords_any" in exp:
        checks.append(("keywords_any", _has_keyword(blob, exp["keywords_any"])))

    return _finalize(checks, {"source": resp.get("source")})


def score_guide_case(case: dict[str, Any], answer: str) -> dict[str, Any]:
    """对讲解文本打分。expect 键见 rule_checks.md。"""
    exp = case.get("expect", {})
    answer = answer or ""
    checks: list[tuple[str, bool]] = []

    if "keywords_any" in exp:
        checks.append(("keywords_any", _has_keyword(answer, exp["keywords_any"])))

    length = len(answer)
    if "min_len" in exp:
        checks.append(("min_len", length >= exp["min_len"]))
    if "max_len" in exp:
        checks.append(("max_len", length <= exp["max_len"]))

    return _finalize(checks, {"length": length, "answer_head": answer[:120]})


def score_intent_case(case: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
    """对 /intent/parse 响应打分。expect 键：duration（等值）/ interests / physical /
    travel_type（均为子集匹配：期望标签都进入 preference 对应字段即通过，多余标签不扣分）。"""
    exp = case.get("expect", {})
    pref = resp.get("preference", {}) or {}
    checks: list[tuple[str, bool]] = []

    if "duration" in exp:
        checks.append(("duration", pref.get("duration") == exp["duration"]))
    for field in ("interests", "physical", "travel_type"):
        if field in exp:
            have = set(pref.get(field, []))
            checks.append((field, all(t in have for t in exp[field])))

    return _finalize(checks, {"source": resp.get("source"), "preference": pref})


def score_review_case(case: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
    """对 /review/content 响应打分。expect 键：decision（等值 pass/revise/block）。

    review 是分类任务（待审核文本 → 裁定），主信号就是 decision 是否等于期望；
    每个 case 单一 check，case 分即 0/1（命中/未命中），run 分 = 分类准确率。
    """
    exp = case.get("expect", {})
    checks: list[tuple[str, bool]] = []
    if "decision" in exp:
        checks.append(("decision", resp.get("decision") == exp["decision"]))

    issues = resp.get("issues", []) or []
    return _finalize(checks, {
        "source": resp.get("source"),
        "decision": resp.get("decision"),
        "n_issues": len(issues),
        "reviewer_notes_head": (resp.get("reviewer_notes") or "")[:120],
    })


def _finalize(checks: list[tuple[str, bool]], detail: dict[str, Any]) -> dict[str, Any]:
    passed = sum(1 for _, ok in checks if ok)
    score = passed / len(checks) if checks else 1.0
    return {
        "checks": [{"name": n, "passed": ok} for n, ok in checks],
        "score": round(score, 3),
        "passed": passed,
        "total": len(checks),
        "detail": detail,
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总 case 结果 → overall + by_category。"""
    overall = sum(r["score"] for r in results) / len(results) if results else 0.0
    by_cat: dict[str, float | None] = {}
    for cat in ("route", "guide", "intent", "review"):
        rs = [r for r in results if r.get("category") == cat]
        by_cat[cat] = round(sum(r["score"] for r in rs) / len(rs), 3) if rs else None
    return {"overall": round(overall, 3), "by_category": by_cat, "n": len(results)}
