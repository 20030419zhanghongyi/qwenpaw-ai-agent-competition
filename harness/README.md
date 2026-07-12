# Harness —— QwenPaw 外层编排 / 评测 / 护栏层

> 「澳跡同行 Macau StoryWalk」在 QwenPaw 之上的**外层 harness**。
> 内层 = QwenPaw(单 agent 运行时);外层 = 本目录(规格/数据/文档)+ `backend/app/` 下的运行时代码。

---

## 1. 一句话定位

QwenPaw 自己就是一个 harness(GitHub 官方 tag:`agent-harness`、`harness-engineering`)。
我们**不重建**它的 agent 循环,而是在它外面套一层,负责:**多 agent 编排、评测调优、护栏、可观测**。

```
┌──────────────────── 外层 harness(我们写)────────────────────┐
│  ① 编排路由   ② 评测调优   ③ 护栏   ④ 可观测/审计   ⑤ 知识管理 │
└───────────────────────────┬──────────────────────────────────┘
                            │  /chats · agents chat · agents create
┌───────────────────────────▼──────────────────────────────────┐
│                  内层 harness(QwenPaw,现成)                  │
│   单 agent 运行时:技能 + 记忆(ReMe)+ 工具 + 沙箱 + Qwen 模型  │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. 为什么需要它(比赛视角)

| 比赛要求 | harness 怎么满足 |
|---|---|
| 智能体调优 | ②评测循环 = 调优的本体,产出**分数曲线 / before-after 对比**,是整份材料最强截图 |
| 开发过程证明(截图) | 外层每一块都是可截图工程产物(见 plan §截图采集清单 8 节点) |
| 场景设计 | ①编排把 6 agent 设计真正跑起来,不是纸上 |
| 区分度 | 比起「QwenPaw 套个聊天框」的队伍,多出 编排+评测+护栏 三层工程 |

> 纯调 DashScope 的队伍只能截一段 JSON 返回;我们在 QwenPaw 上做 + 外层 harness,**证据更厚**。这就是用 QwenPaw 的隐藏红利。

---

## 3. 五个模块

| 模块 | 职责 | 复用现有资产 |
|---|---|---|
| ① 编排路由 orchestrator | 用户意图 → 分给哪个 agent(讲解/路线/需求);可 `agents chat` 让 agent 互相对话 | 设计中的 6 agent |
| ② 评测调优 eval | 测试集 → 跑 QwenPaw → 打分(LLM-judge / 规则)→ 看哪差 → 改 SKILL.md → 再跑 | 小红书 100 笔记 / 751 评论 = 天然测试集 |
| ③ 护栏 guardrails | 调用前注入 ethics base;调用后跑 content-safety-review + 事实核对 + 低置信回退 | `ethics/qwenpaw-skills/` 4 个技能 |
| ④ 可观测 observability | 每次调用 trace 落库(input/agent/skill/output/延迟/token) | `ethics/实施清单.md §3` 审计日志 |
| ⑤ 知识管理 knowledge | RAG pipeline 把 POI / 小红书喂进 agent 的 memory / file_store | `rag/ingest.py`、`data/` |

> **红线**:外层不重复造内层已有的能力(memory / tool calling / sandbox 留给 QwenPaw)。重复造轮子反而稀释「用了 QwenPaw」的证明。

---

## 4. 目录约定

本仓库 harness 相关内容分两处,**规格与运行时分离**(对标 `ethics/` 的做法):

**`harness/`(本目录)= 规格 / 数据 / 产出 / 文档,不放运行时代码**
```
harness/
├── README.md            # 本文件
├── plan.md              # 开发计划(分阶段 + 截图清单)
├── datasets/            # 评测测试用例(澳门文旅 query)
├── rubrics/             # 打分标准(LLM-judge prompt / 规则)
├── results/             # 跑批产出(分数表、曲线图)
└── reports/             # 评测报告 / 调优记录
```

**`backend/app/` = 运行时代码**
```
backend/app/
├── agents/
│   └── qwenpaw_client.py   # 连接 QwenPaw:登录 + POST /chats + 收回复
├── orchestrator/           # ① 意图路由 / 多 agent 分发
├── eval/                   # ② 跑批 + 打分
├── guardrails/             # ③ 前后置 hook
└── observability/          # ④ trace / 审计落库
```

---

## 5. 与现有仓库的关系

| 现有部分 | 在 harness 里的角色 |
|---|---|
| `ethics/qwenpaw-skills/` | 护栏 skill:既挂进内层 agent,也作外层 guardrail hook(两层都能截图) |
| `rag/`、`data/` | 知识 pipeline,产出喂给 agent memory / file_store |
| `backend/app/agents/` | QwenPaw 调用封装(harness 的连接层住这里) |
| `backend/app/features/routes/` | 业务接口;harness 接管其 AI 部分(讲解 / 路线微调) |
| QwenPaw `localhost:8088` | 内层 harness,被外层驱动 |

---

## 6. 连接方式(已在本机确认)

- QwenPaw 已在跑:`http://127.0.0.1:8088/`(conda env `qwenpaw`,经 `~/Desktop/启动QwenPaw.sh` 启动)
- **`/chats`** HTTP API —— 单 agent 对话(会话 CRUD + 发消息)
- **`agents chat --from-agent X --to-agent Y --text "..."`** —— 多 agent 协作
- **`agents create --name "..." --agent-id ...`** —— CLI 直接建 agent(不必走 UI)
- **web 鉴权**(`qwenpaw auth`,有 web 账号)—— 后端调 REST 前需先登录拿 session / token(**接线时唯一要处理的小坑**)
- 技能加载:文件夹放进 `~/.qwenpaw/skill_pool/` → `qwenpaw skills list` 自动发现 → Console / `qwenpaw skills config` 启用;打包分发用 `plugin install <本地路径>`

> `/chats` 确切的「发消息 + 流式回复」子路由,接线时在 Console 浏览器 devtools Network 面板抓一条真实请求即可确认。

---

## 7. 当前状态(2026-07-12)

- ✅ QwenPaw 部署完成(进程 + Console 200,API base `/api`,version `1.1.12.post3`)—— 基础部署达标
- ✅ 已有实验 agent `QwenPaw_QA_Agent_0.2` + 自定义技能 `QA_source_index`(证明「会写 skill」)
- ✅ 模型 provider 已配(Aliyun token plan;deepseek / glm 可测)
- ✅ ethics 4 技能已有 prompt.md 草稿(`ethics/qwenpaw-skills/`)
- ✅ **harness 骨架就位**:`harness/{datasets,rubrics,results,reports}` + `backend/app/{orchestrator,eval,guardrails,observability}` + `skills/` 全部建好
- ✅ **P0 连接基座完成 + 端到端验证**:`qwenpaw_client.py`(契约 `POST /api/console/chat` SSE + `X-Agent-Id`) + `/agents/ping` + `trace.py`;`ask()` 已真实跑通(default agent,干净答复 + token/延迟落 trace)
- ✅ **P1 路线 agent 完成 + 端到端验证(2026-07-12)**:QwenPaw 建 `route` agent + 挂 `route-adjust` 技能(reconcile 法见 `skills/README.md`)+ `.env` `ROUTE_AGENT_ENABLED=true`;thin prompt(无 schema)返回干净结构化 JSON;`POST /api/v1/routes/adjust` 实测 **`source=agent`**(agent 把「少走点路」→ `physical:less-walk` + `remove_tail`,引擎裁末端、压到 2.4km)。**待**:截图③④⑦采集
- 🟢 **P2 评测/调优 harness 骨架完成**:`datasets/cases.json`(17 条真实取材)+ `rubrics/`(规则+LLM-judge)+ `eval/{runner,scoring,compare}.py`;route 规则 baseline 已跑(overall **0.796**),出图工具已验证;**待**:把烟测改打 `route` agent 重跑 → 真实 before/after(截图⑥)+ 建讲解 guide agent
- ⬜ 护栏 hook(P3)、可观测落库(P4)—— 待建

---

## 8. 下一步

**立即**:采集 P1 截图③(建 agent)④(技能 source=custom)⑦(后端 `source=agent` 真实调整);然后把 `scripts/test_route_agent_smoke.py` 从 `default`+自带 schema 改成直打 `route` agent(thin prompt),重跑 9 条拿真实 before/after 分数(对规则 baseline 0.796,截图⑥)。

**之后**:进 **[`plan.md`](./plan.md) P2(评测/调优 harness,核心)** —— 文化讲解 agent + 测试集 + rubric + 跑批,产出分数曲线 / before-after(整份材料最强证据)。
