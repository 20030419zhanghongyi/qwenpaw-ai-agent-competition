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
├── prompt.md       # 该 Agent 的 system prompt（贴进 QwenPaw）
├── config.yaml     # QwenPaw 配置占位（模型/温度/工具/输入输出 schema）
└── examples/       # few-shot 样例（输入 → 期望输出）
```

> 所有 prompt 都以 [`../prompts/_ethics_base.md`](../prompts/_ethics_base.md) 为共享前缀。

## 如何在 QwenPaw 平台配置（步骤，团队按平台实际 UI 微调）

1. 在 QwenPaw/百炼控制台新建 Agent。
2. System prompt = `_ethics_base.md` 全文 + 本技能 `prompt.md` 职责段。
3. 按技能需要挂载工具（RAG 检索 / 地图 / 天气 / 视觉）。
4. 用 `examples/` 里的样例做 few-shot 与回归测试。
5. 记录该技能的 `model_version`、`prompt_version`，供审计日志（见 `实施清单.md` §3）。

## 与后端代码的关系

后端 `backend/app/agents/` 封装对这些 QwenPaw Agent 的调用（认证、重试、输出 schema 校验、审计落库）。
本目录只放**规格**（prompt/配置/样例），不放运行时代码。Prompt 改动走版本号。
