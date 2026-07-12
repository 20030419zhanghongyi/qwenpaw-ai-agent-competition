"""route agent 烟测（Tier 0：不依赖在 QwenPaw 建 route agent / 开 .env）。

目的：在动手做 QwenPaw 手动配置之前，先证明「模型能把自然语言翻成正确的结构化意图」。
做法：用**自带 schema 的自包含 prompt**（因为 default agent 没挂 route-adjust 技能）调
`default` agent，再用**真实的** `route_agent._extract_json + _coerce` 解析——即只替换
「agent id」和「prompt 是否自带 schema」两处，解析/清洗/叠加逻辑全是生产代码。

跑通说明：模型能力 OK，值得去做手动配置；之后 route agent 挂上技能后，thin prompt 也能
工作（schema 由技能 system prompt 提供）。
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.agents import route_agent  # noqa: E402
from app.agents.qwenpaw_client import QwenPawClient  # noqa: E402
from app.models.user import Preference  # noqa: E402

CASES_PATH = Path(__file__).resolve().parents[1] / "harness" / "datasets" / "cases.json"

SCHEMA_BLOCK = """请输出严格 JSON（第一个字符必须是 {，不要代码围栏、不要解释），schema 如下：
{
  "preference_add": {
    "interests": ["从 history/architecture/food/photo/culture 中选，可多个"],
    "physical":  ["从 normal/less-walk/no-backtrack 中选，可多个"],
    "duration":  "half-day | full-day | evening | custom（不变则省略或 null）"
  },
  "add_nodes":          ["photo 或 food，表示要实际插入的节点类型"],
  "remove_tail":        true/false,
  "reorder_by_district": true/false,
  "notes":              "一句话说明"
}
判定要点：
- 「少走路/累/坐车/腿脚不好」→ physical 加 less-walk；要明显减负再 remove_tail=true。
- 「别绕路/顺路/不回头」→ physical 加 no-backtrack，reorder_by_district=true。
- 「拍照/出片/颜色好看」→ interests 加 photo，add_nodes 加 photo。
- 「吃/小吃/美食/顺便吃个饭」→ interests 加 food，add_nodes 加 food。
- 「只逛半天/时间不够」→ duration 改 half-day。
- 没提到的字段给空数组/null/false，不要瞎编。"""


def build_prompt(instruction: str, pref: Preference, route_id: str) -> str:
    return (
        "你是路线微调助手。把用户的自然语言调整指令翻成结构化意图。\n"
        "当前用户偏好：" + json.dumps(pref.model_dump(), ensure_ascii=False) + "\n"
        "当前路线模板 id：" + route_id + "\n"
        "用户调整指令：" + instruction.strip() + "\n\n" + SCHEMA_BLOCK
    )


# 每条 case 的期望（用来自动判 ✓/✗）；只断言关键意图，不强求全等
EXPECTED = {
    "r01": {"physical": "less-walk", "remove_tail": True},
    "r02": {"add_nodes": "photo", "interests": "photo"},
    "r03": {"reorder_by_district": True, "physical": "no-backtrack"},
    "r04": {"add_nodes": "food", "interests": "food"},
    "r05": {"physical": "less-walk"},
    "r07": {"duration": "half-day"},
    "r08": {"physical": "less-walk", "interests": "photo"},
    "r09": {"physical": "less-walk", "add_nodes": "food"},
    # r06「小众/别挤大三巴」无结构化字段，跳过自动判定
}


def judge(adj, eid: str) -> tuple[bool, str]:
    exp = EXPECTED.get(eid)
    if not exp:
        return True, "(无结构化期望，跳过判定)"
    miss = []
    if "physical" in exp and exp["physical"] not in adj.preference_add_physical:
        miss.append(f"physical缺{exp['physical']}")
    if "interests" in exp and exp["interests"] not in adj.preference_add_interests:
        miss.append(f"interests缺{exp['interests']}")
    if "duration" in exp and adj.preference_add_duration != exp["duration"]:
        miss.append(f"duration期望{exp['duration']}实得{adj.preference_add_duration}")
    if "add_nodes" in exp and exp["add_nodes"] not in adj.add_nodes:
        miss.append(f"add_nodes缺{exp['add_nodes']}")
    if exp.get("remove_tail") and not adj.remove_tail:
        miss.append("缺remove_tail")
    if exp.get("reorder_by_district") and not adj.reorder_by_district:
        miss.append("缺reorder_by_district")
    return (not miss), ("✓" if not miss else "✗ " + ", ".join(miss))


def run_one(c, qp):
    pref = Preference(**c["context"]["preference"])
    prompt = build_prompt(c["input"], pref, c["context"]["route_id"])
    t0 = time.perf_counter()
    try:
        raw = qp.ask("default", prompt, session_id=f"route-smoke-{c['id']}")
    except Exception as exc:
        return c["id"], c["input"], None, None, f"call_failed: {exc}", int((time.perf_counter()-t0)*1000)
    obj = route_agent._extract_json(raw)
    if obj is None:
        return c["id"], c["input"], raw, None, "parse_failed", int((time.perf_counter()-t0)*1000)
    try:
        adj = route_agent._coerce(obj)
    except Exception as exc:
        return c["id"], c["input"], raw, None, f"coerce_failed: {exc}", int((time.perf_counter()-t0)*1000)
    ok, note = judge(adj, c["id"])
    return c["id"], c["input"], raw, adj, note, int((time.perf_counter()-t0)*1000)


def main():
    cases = [c for c in json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
             if c["category"] == "route"]
    qp = QwenPawClient()
    print(f"=== route agent 烟测 | agent=default | {len(cases)} cases ===\n", flush=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(run_one, c, qp): c for c in cases}
        results = {}
        for fut in as_completed(futs):
            cid, inp, raw, adj, note, ms = fut.result()
            results[cid] = (inp, raw, adj, note, ms)
            flag = "✓" if note.startswith("✓") or note.startswith("(") else "✗"
            print(f"[{cid}] {flag} {note}  ({ms}ms)", flush=True)
    # 详细打印失败/可疑的
    print("\n=== 详情（结构化意图） ===", flush=True)
    for cid in sorted(results):
        inp, raw, adj, note, ms = results[cid]
        print(f"\n--- {cid} ---  {inp}")
        if adj:
            print(f"  RouteAdjustment: {adj.model_dump_json()}")
        else:
            print(f"  raw: {(raw or '')[:200]}")


if __name__ == "__main__":
    main()
