# 规则项打分标准（rule_checks）

> 零成本、可重复 —— 评测的主力打分方式（plan.md §5）。每条 case 的 `expect`
> 字段定义若干**可机器核对**的检查项，每项 0/1，case 分 = 通过项 / 总项。
> run 分 = 全部 case 分的均值（0–1，也按 category 分别统计）。
> 由 `backend/app/eval/scoring.py` 实现，对应 `harness/datasets/cases.json` 的 `expect` 键。

## route 类（对 `/routes/adjust` 响应打分）

响应里可用的核对源：`preference_after`、`route.nodes`、`added_nodes`、`removed_nodes`、
`reordered_nodes`、`applied_constraints`、`rationale`、`explanation`。

| expect 键 | 检查逻辑 | 通过条件 |
|---|---|---|
| `physical: [tag,...]` | 每个 tag 是否进了 `preference_after.physical` | 全部命中 = 1 |
| `interests: [tag,...]` | 每个 tag 是否进了 `preference_after.interests` | 全部命中 = 1 |
| `duration: "half-day"` | `preference_after.duration == 值` | 命中 = 1 |
| `added_tag: "photo"\|"food"` | `added_nodes` 里是否存在该兴趣的 POI（按 POI `suitable_for` 判定） | 存在 = 1 |
| `removed_tail: true` | `removed_nodes` 非空（或 route.nodes 少于模板） | 非空 = 1 |
| `keywords_any: [k,...]` | 任一关键词出现在 `applied_constraints`/`rationale`/`explanation.summary` 拼接文本里 | 命中 ≥1 = 1 |

> route 类用这套规则**即等价于规则版的自检** —— agent 版与规则版应同样通过这些项，
> agent 版的价值在**语义覆盖**（能处理规则关键词没覆盖的自然语言），由 LLM-judge + 扩展用例衡量。

## guide 类（对讲解 agent 文本打分）

| expect 键 | 检查逻辑 | 通过条件 |
|---|---|---|
| `keywords_any: [k,...]` | 任一关键词（不区分大小写）出现在讲解文本里 | 命中 ≥1 = 1 |
| `min_len: N` | 文本字符数 ≥ N | 满足 = 1 |
| `max_len: N` | 文本字符数 ≤ N（过长=不精炼） | 满足 = 1 |

> 关键词命中只验证「讲到了相关事实」，**不验证事实正确性** —— 后者交给 LLM-judge
> + ethics `source-attribution`（见 `llm_judge_prompt.md`）。易变信息（开放时间/活动）
> 类用例，期望 agent 触发「以现场为准」措辞（g08）。

## 记分产出（落 `harness/results/scores_<run>.json`）

```
{
  "run_id": "...", "agent_map": {"route":"route","guide":"guide"}, "ts": "...",
  "overall": 0.0,                       # 0–1
  "by_category": {"route": 0.0, "guide": 0.0},
  "cases": [ {"id","category","checks":[{"name","passed"}],"score":0.0,"detail":...}, ... ]
}
```
