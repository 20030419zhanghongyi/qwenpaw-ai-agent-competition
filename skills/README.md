# skills/ —— 仓库级技能源（非伦理类）

本目录存放面向 QwenPaw agent 的**技能源**（`SKILL.md`），平行于 `ethics/qwenpaw-skills/`（伦理类）。

```
skills/
├── route-adjust/SKILL.md   # P1：路线微调 agent 的技能（NL 偏好 → 结构化意图 JSON）
└── macau-guide/SKILL.md    # P2：文化讲解 agent 的技能（POI 资料 → 有据讲解 + 来源/置信）
```

## 部署到 QwenPaw（开发期）

开发期用「文件夹丢 skill_pool」的方式批量加载（plan.md §5）。

> ⚠️ **2026-07-12 实测纠正**：早期文档说「丢进 `~/.qwenpaw/skill_pool/` → `qwenpaw skills list`
> 自动发现」——**不成立**。`qwenpaw app` 启动**不扫描** pool 目录，`qwenpaw skills list` 只列
> 已挂到某 agent 的技能，`qwenpaw skills install` 只收 http(s) URL 不收本地路径。丢进去的文件夹不会
> 进清单 `skill_pool/skill.json`，Console 技能网格也看不到。**必须显式触发 reconcile**：

```bash
# 1. 复制技能源到 QwenPaw 技能池
cp -R skills/route-adjust skills/macau-guide ~/.qwenpaw/skill_pool/

# 2. 校验 SKILL.md 格式通过（safe=True 才会被登记）
qwenpaw skills test ~/.qwenpaw/skill_pool/route-adjust

# 3. 触发 pool reconcile：扫盘 → 写进 skill_pool/skill.json（source=customized）
#    方式 A（API，推荐）：app 在跑时调一次即可
curl -X POST http://127.0.0.1:8088/api/skills/pool/refresh
#    方式 B：Console → Skills 页若有 Refresh 按钮，点它
#    之后刷新 Console 页面，route-adjust 就出现在技能网格里

# 4. 在 Console Create New Agent / Skills 页给目标 agent 勾选启用该技能
```

## 在 QwenPaw 里建路线 agent（P1 手动步骤）—— ✅ 已完成 + 端到端验证（2026-07-12）

CLI 默认不在 PATH 时，用 **Console** 建：

1. Console → Create New Agent：name `路线微调`，agent-id `route`，挑一个已配的 text 模型
2. 确认 `qwenpaw agents list` / `GET /api/agents` 能看到 `route`
3. 给该 agent 启用 `route-adjust` 技能（按上节「部署」先 reconcile 进清单）
4. 仓库 `.env` 设 `ROUTE_AGENT_ENABLED=true`，重启后端 → `/routes/adjust` 走 agent 驱动

> **验证状态**：已完成。`route` agent + `route-adjust` 技能就位，thin prompt（不带 schema、靠技能
> system prompt）返回干净结构化 JSON；`POST /api/v1/routes/adjust` 实测 `source=agent`，agent 把
> 「少走点路」翻成 `physical:less-walk` + `remove_tail`，排线引擎据此裁末端、压到 2.4km。
>
> **两个坑（已踩过）**：
> - **技能不自动发现**：见上节，必须 `POST /api/skills/pool/refresh`。
> - **模型 provider 401**：建 agent 时若被分到 key 失效的 provider，会 `MODEL_UNAUTHORIZED_ACCESS`、
>   `completion_tokens:0`、返回空串且秒退（~1.5s）。换到可用 provider（如 default 用的那个）即通。
>   症状：空返回 + 秒退 + `qwenpaw.log` 里 `openai.AuthenticationError 401`。

## 在 QwenPaw 里建讲解 agent（P2 手动步骤）

讲解 agent（`guide`）的技能源已就位（`skills/macau-guide/SKILL.md`），与路线 agent 平行：

1. Console → Create New Agent：name `文化讲解`，agent-id `guide`，挑已配的 text 模型
2. `cp -R skills/macau-guide ~/.qwenpaw/skill_pool/` → `qwenpaw skills test` → `curl -X POST http://127.0.0.1:8088/api/skills/pool/refresh`（同上，**不自动发现**）
3. 给该 agent 启用 `macau-guide` 技能（讲解类，对齐 `ethics/qwenpaw-skills/source-attribution`）
4. 待 `POST /api/v1/guide/generate`（POI + 偏好 → 讲解）接口落地后即可端到端联调；
   在此之前，讲解用例 g01–g08 的评测 `by_category.guide` 仍为 null（见 `harness/results/`）

> `macau-guide` 输出严格 JSON `{text, source_type, confidence, ai_generated, language}`：
> 易变信息（开放时间/活动）置信度 ≤0.5 且正文「以现场为准」，不编史料——
> 与路线技能同一套「结构化输出 + 失败降级」纪律。
