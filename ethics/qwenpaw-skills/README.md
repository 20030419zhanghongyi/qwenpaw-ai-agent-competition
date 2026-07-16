# QwenPaw 伦理技能（qwenpaw-skills/）

这里存放产品运行时、在 **QwenPaw** 上配置的伦理相关 Agent 技能。每个子目录是一个技能：

| 技能 | 职责 | 对应原则 | 初赛优先 |
|------|------|----------|----------|
| [`source-attribution/`](./source-attribution/) | 给讲解/识别结果打来源标签 + 置信度，低置信回退 | 透明度 | ⭐ 先做 |
| [`anti-sycophancy/`](./anti-sycophancy/) | 纠正用户错误假设、不编史料、不逢迎 | 人类控制 | ⭐ 先做 |
| [`content-safety-review/`](./content-safety-review/) | 高风险内容上线前审核、敏感文化主题把关 | 问责制 + 安全 | 后做 |
| [`fairness-gate/`](./fairness-gate/) | 推荐输入特征白名单 + 跨语言一致性守门 | 公平性 | 后做 |

## 每个技能目录约定

```
<skill>/
├── SKILL.md        # QwenPaw 可加载的技能（frontmatter + 内联伦理基线 + 职责/规则/样例）
├── prompt.md       # 原始 system prompt 规格（SKILL.md 来源，保留供审阅/版本管理）
└── config.yaml     # QwenPaw 配置占位（模型/温度/工具/输入输出 schema，可选）
```

> `SKILL.md` 已把 [`../prompts/_ethics_base.md`](../prompts/_ethics_base.md) 共享前缀**内联**进每个技能，
> 故技能自包含；`prompt.md` 的「System prompt = base 前缀 + 本文件」约定由 `SKILL.md` 落实。

## 已接入 QwenPaw（2026-07-13）✅

4 个 ethics 技能都已生成 `SKILL.md` 并注册进 QwenPaw skill pool（`source=customized`，共 25 个技能）：

```bash
cp -R ethics/qwenpaw-skills/{source-attribution,anti-sycophancy,content-safety-review,fairness-gate} ~/.qwenpaw/skill_pool/
curl -X POST http://127.0.0.1:8088/api/skills/pool/refresh   # 不自动发现，必须 reconcile
```

> 与 route-adjust / requirement-understand 同一套注册流程（见 `skills/README.md`，**不自动发现**坑）。

### 挂到哪个 agent（Console → 给 agent 勾选启用技能）

| 技能 | 挂载目标 | 作用 |
|------|----------|------|
| `source-attribution` | guide（讲解）、photo（拍照识别讲解） | 输出标 source_type/confidence，低置信回退 |
| `anti-sycophancy` | guide（讲解） | 纠正用户错误假设，不逢迎不编史料 |
| `fairness-gate` | intent（需求理解，作后置复核） | 结构化偏好不得含禁止特征 |
| `content-safety-review` | 独立审核 agent / 外层 guardrail hook（P3） | 高风险内容上线前 pass/revise/block |

> `backend/app/guardrails/` 已落地文本隔离、Agent/上传端点分级限流、去标识 trace 与 PostgreSQL 审计。
> guide/photo 输出仍通过 reviewer 管道审核；共享伦理基线继续由 Console 技能挂载到内层 Agent，两层均需保留运行证据。

### 配置要点（团队按平台实际 UI 微调）

1. 在 QwenPaw Console 给目标 agent 勾选启用对应 ethics 技能（技能正文已是完整 system prompt）。
2. 按技能需要挂载工具（RAG 检索 / 地图 / 天气 / 视觉）。
3. 记录该技能的 `model_version`、`prompt_version`，供审计日志（见 `实施清单.md` §3）。

## 与后端代码的关系

后端 `backend/app/agents/` 封装对这些 QwenPaw Agent 的调用（认证、重试、输出 schema 校验、审计落库）。
本目录只放**规格**（prompt/配置/样例），不放运行时代码。Prompt 改动走版本号。
