"""评测跑批 runner（P2 核心）。

读 harness/datasets/cases.json → 逐条调对应能力 → 规则打分 → 落 harness/results/。
- route 类：POST /api/v1/routes/adjust（经 TestClient，走真实端点；ROUTE_AGENT_ENABLED 决定 agent/规则）
- guide 类：qwenpaw_client.ask(guide_agent) —— 真实 LLM 调用，可用 --skip-guide 跳过省 token

用法：
    python -m app.eval.runner --only route --run-id rules-baseline   # 纯规则，0 token
    python -m app.eval.runner --run-id full --guide-agent default    # 含 guide（耗 token）
    python -m app.eval.runner --only guide --guide-agent guide --limit 2

调优循环：改 SKILL.md/启用 agent 后换个 --run-id 重跑，scores_*.json 两两对比出 before/after。
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.agents.qwenpaw_client import QwenPawClient, QwenPawError
from app.core.config import settings
from app.db.data import get_poi
from app.observability.trace import record_trace

from . import scoring

logger = logging.getLogger("macau_storywalk.eval")

CASES_PATH = settings.repo_root / "harness" / "datasets" / "cases.json"
RESULTS_DIR = settings.repo_root / "harness" / "results"


def run_route_case(case: dict, client: TestClient) -> dict:
    """调真实 /routes/adjust 端点。"""
    req = {
        "route_id": case["context"]["route_id"],
        "instruction": case["input"],
        "preference": case["context"]["preference"],
    }
    resp = client.post("/api/v1/routes/adjust", json=req)
    return resp.json()


def run_guide_case(case: dict, qp: QwenPawClient, guide_agent: str) -> str:
    """调讲解 agent。POI 名注入 prompt，确保即便无专门 guide agent 也能作答。"""
    poi = get_poi(case["context"]["poi_id"]) or {}
    name = poi.get("name_zh", case["context"]["poi_id"])
    prompt = (
        f"你是澳门文旅讲解员。用户在「{name}」提问：{case['input']}\n"
        f"请用中文讲解（150 字以内）。涉及年代/开放时间等不确定的，要标注「以现场为准」或「示意」。"
    )
    try:
        return qp.ask(guide_agent, prompt, session_id=f"eval-guide-{case['id']}")
    except QwenPawError as exc:
        logger.warning("guide 调用失败 %s：%s", case["id"], exc)
        return ""


def run_intent_case(case: dict, client: TestClient) -> dict:
    """调真实 /intent/parse 端点（INTENT_AGENT_ENABLED 决定 agent/规则）。"""
    resp = client.post("/api/v1/intent/parse", json={"text": case["input"]})
    return resp.json()


def run_review_case(case: dict, client: TestClient) -> dict:
    """调真实 /review/content 端点（REVIEWER_AGENT_ENABLED 决定 agent/规则）。"""
    resp = client.post("/api/v1/review/content", json={"text": case["input"]})
    return resp.json()


def main() -> None:
    ap = argparse.ArgumentParser(description="harness 评测跑批")
    ap.add_argument("--cases", default=str(CASES_PATH))
    ap.add_argument("--run-id", default=None, help="本次 run 名（默认 run-<ts>）")
    ap.add_argument("--guide-agent", default="default", help="讲解类调用的 agent id")
    ap.add_argument("--only", choices=["route", "guide", "intent", "review"], default=None)
    ap.add_argument("--skip-guide", action="store_true", help="跳过 guide 类（省 LLM token）")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]
    if args.only:
        cases = [c for c in cases if c["category"] == args.only]
    if args.skip_guide:
        cases = [c for c in cases if c["category"] != "guide"]
    if args.limit:
        cases = cases[: args.limit]

    run_id = args.run_id or f"run-{int(time.time())}"
    print(f"=== eval run: {run_id} | {len(cases)} cases | guide_agent={args.guide_agent} ===")

    tc = TestClient(app_get())
    qp = QwenPawClient()

    results = []
    for c in cases:
        if c["category"] == "route":
            resp = run_route_case(c, tc)
            scored = scoring.score_route_case(c, resp)
        elif c["category"] == "intent":
            resp = run_intent_case(c, tc)
            scored = scoring.score_intent_case(c, resp)
        elif c["category"] == "review":
            resp = run_review_case(c, tc)
            scored = scoring.score_review_case(c, resp)
        else:
            answer = run_guide_case(c, qp, args.guide_agent)
            scored = scoring.score_guide_case(c, answer)

        scored["id"] = c["id"]
        scored["category"] = c["category"]
        results.append(scored)
        flag = "✓" if scored["score"] >= 0.99 else ("·" if scored["score"] > 0 else "✗")
        print(f"  {flag} {c['id']:4} {c['category']:5} {scored['score']:.2f}  "
              f"({scored['passed']}/{scored['total']})")

    agg = scoring.aggregate(results)
    out = {
        "run_id": run_id,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "guide_agent": args.guide_agent,
        "overall": agg["overall"],
        "by_category": agg["by_category"],
        "n": agg["n"],
        "cases": results,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"scores_{run_id}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\noverall: {agg['overall']:.3f} | route: {agg['by_category'].get('route')} | "
          f"guide: {agg['by_category'].get('guide')} | intent: {agg['by_category'].get('intent')} | "
          f"review: {agg['by_category'].get('review')} | n={agg['n']}")
    print(f"→ {path}")
    record_trace(kind="eval.run", status="ok", extra={"run_id": run_id, "overall": agg["overall"], "n": agg["n"]})


def app_get():
    """懒加载 app（避免 import 时副作用）。"""
    from app.main import app
    return app


if __name__ == "__main__":
    main()
