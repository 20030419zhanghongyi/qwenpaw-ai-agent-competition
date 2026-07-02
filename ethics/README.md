# ethics/ — 伦理技能中心（基于 QwenPaw）

本目录是「澳跡同行 Macau StoryWalk」**所有伦理相关产物**的家：从原则到工程产物，再到 QwenPaw 上运行的伦理 Agent 技能。

> 产品 AI 能力最终**基于 QwenPaw** 构建。本目录里的「skill」= 在 QwenPaw 上配置、产品运行时负责伦理的 Agent/技能（内容审核、反逢迎、来源标注、公平性闸门）。

## 三层关系（别搞混）

```
docs/AI-Ethics-Policy/   ← 政策层：为什么、什么原则（三语，已存在，不动）
ethics/                  ← 实施层：做成什么产物 + QwenPaw 伦理技能规格（本目录）
backend/app/agents/      ← 运行层：调用 QwenPaw 的代码封装（引用本目录的 prompt）
plan/开发计划与清单.md   ← 排期与验收：伦理任务在哪个阶段做、KPI、责任人（见 §11「伦理落地」）
```

- 想知道**为什么**有这条伦理要求 → 看 `../docs/AI-Ethics-Policy/`
- 想知道**要做出什么**（代码字段/UI/测试/流程）→ 看 [`实施清单.md`](./实施清单.md)
- 想知道 QwenPaw 上**配哪个伦理 Agent、Prompt 怎么写** → 看 [`qwenpaw-skills/`](./qwenpaw-skills/)
- 想知道**什么时候做、谁负责、怎么验收** → 看 [`../plan/开发计划与清单.md`](../plan/开发计划与清单.md) §11

## 目录结构

```
ethics/
├── README.md                  # 本文件
├── 实施清单.md                 # 七原则 → 工程产物 → 勾选项（人看的总表）
├── qwenpaw-skills/            # QwenPaw 上配置的伦理 Agent 技能
│   ├── README.md              # 如何在 QwenPaw 平台配置这些技能
│   ├── content-safety-review/ # ① 内容安全与来源审核（高风险内容上线前审核）
│   ├── anti-sycophancy/       # ② 反逢迎与文化准确（不编史料、纠正错误假设）
│   ├── source-attribution/    # ③ 来源标注与置信度（source_type + confidence）
│   └── fairness-gate/         # ④ 公平性闸门（输入特征白名单 + 跨语言一致性）
├── prompts/
│   └── _ethics_base.md        # 共享伦理基线 Prompt，注入所有 QwenPaw Agent
└── checks/                    # 本地可跑的伦理合规测试/脚本（占位）
    └── README.md
```

## 七原则 → QwenPaw 伦理技能 映射

| 伦理原则 | 落地的 QwenPaw 技能 | 也在工程层做 |
|----------|---------------------|--------------|
| 公平性 | `fairness-gate` | `features/routes/matcher.py` 输入白名单 + `checks/test_fairness` |
| 透明度 | `source-attribution` | POI `source_type`、AI 徽章、推荐理由、置信度 |
| 问责制 | `content-safety-review` | 审计日志、责任人、版本号 |
| 私隐 | （非 Agent，工程层为主） | 最小注册、授权开关、图片脱敏、数据接口 |
| 安全可靠 | `content-safety-review` | 路线 `reviewed`、约束兜底、限流、注入防护 |
| 人类控制 | `anti-sycophancy` | 路线可改、确认后播、开关、反逢迎 Prompt |
| 政策遵循 | （治理流程） | 合规映射表、`source/license` 字段、反馈闭环 |

## 怎么用（开发流程）

1. **配置 QwenPaw 技能**：把 `qwenpaw-skills/<skill>/prompt.md` 贴进 QwenPaw 平台对应 Agent 的 system prompt，`_ethics_base.md` 作为共享前缀。
2. **后端调用**：`backend/app/agents/` 封装这些 QwenPaw Agent 的调用，运行时读取本目录 prompt（或平台已配置）。
3. **本地检查**：`checks/` 下的测试/脚本在 CI 或提交前跑，确保没回归（如跨语言一致性）。
4. **对照清单**：每做完一项，回 [`实施清单.md`](./实施清单.md) 打勾。

## 与初赛的关系

初赛最小伦理包（见 [`实施清单.md`](./实施清单.md) §9）已能覆盖 7 原则的可见面。
其中 4 个 QwenPaw 技能建议优先配 `source-attribution` 和 `anti-sycophancy`（演示价值最高、成本最低）。
