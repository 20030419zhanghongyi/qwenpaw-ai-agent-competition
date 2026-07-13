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
>
> **2026-07-13 实测（rule-check 饱和）**：guide 的 before/after = `default` agent（无技能）
> vs `guide` agent（macau-guide 技能），8 case 两边**都 1.0**（见 `scores_guide-baseline.json` /
> `scores_guide-agent.json`）。知名 POI 的基本事实覆盖 + 易变信息 hedging（g08 两边都说「以现场为准」）
> 任何合格 LLM 都能做到，故 keyword+长度 rubric **在 guide 上饱和、无区分度**。guide agent 的真正
> 价值——结构化 `{text,source_type,confidence}`、严格不编造、JSON 契约——是 rule-check 抓不到的
> 质量维度，已由 **guide→reviewer 管道**（`/guide/generate` 产出过 `review_text` 把关）兜住，
> 更深一层的事实正确性留 LLM-judge。

## intent 类（对 `/intent/parse` 响应打分）

响应里可用的核对源：`preference`（NL → 结构化偏好的解析结果）。

| expect 键 | 检查逻辑 | 通过条件 |
|---|---|---|
| `duration: "full-day"` | `preference.duration == 值` | 命中 = 1 |
| `interests: [tag,...]` | 每个 tag 是否进入 `preference.interests`（子集匹配，多余标签不扣分） | 全部命中 = 1 |
| `physical: [tag,...]` | 每个 tag 是否进入 `preference.physical`（子集匹配） | 全部命中 = 1 |
| `travel_type: [tag,...]` | 每个 tag 是否进入 `preference.travel_type`（子集匹配） | 全部命中 = 1 |

> intent 类天然适合规则打分（输出是结构化 Preference，非自由文本）。agent 版的价值在
> **语义覆盖**：规则版只认字面关键词，agent 能理解「一日游→full-day」「腿脚不太好→less-walk」
> 「重复的路→no-backtrack」等同义表达 —— 这些 case（i02/i08）构成 agent vs 规则的 before/after 差。

## review 类（对 `/review/content` 响应打分）

响应里可用的核对源：`decision`（pass / revise / block）、`issues`、`reviewer_notes`。

| expect 键 | 检查逻辑 | 通过条件 |
|---|---|---|
| `decision: "pass"\|"revise"\|"block"` | `resp.decision == 值` | 命中 = 1 |

> review 是**分类任务**（待审核文本 → 裁定），主信号即 decision 是否等于期望，故每 case 单一
> check、case 分 0/1，run 分 = 分类准确率。agent 版的价值在**语义判断**：规则版只做关键词红线
> 扫描，(a) 漏判语义性风险 —— 价值/效力断言（v04）、诱导脱离平台交易（v05）、医疗越界（v08）
> 均无关键词命中会误 pass；(b) 过判可更正的事实错误 —— 「拨打120」（澳门应为 999，v06）规则
> 版会误 block，agent 正确判 revise。这些 case 构成 agent vs 规则的 before/after 差。

## 记分产出（落 `harness/results/scores_<run>.json`）

```
{
  "run_id": "...", "agent_map": {"route":"route","guide":"guide"}, "ts": "...",
  "overall": 0.0,                       # 0–1
  "by_category": {"route": 0.0, "guide": 0.0, "intent": 0.0, "review": 0.0},
  "cases": [ {"id","category","checks":[{"name","passed"}],"score":0.0,"detail":...}, ... ]
}
```
