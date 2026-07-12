# Harness 开发计划(执行主干)

> 配套 [`README.md`](./README.md)。**这是唯一执行主干**,路线细节已并入,只跟这一份。
> 对齐项目主线(M3 Agent 联调 07/30、M4 行走中能力 08/06)与**初赛截止 2026-08-09**。今天 2026-07-09,剩约 4.5 周。
> **当前优先:先把路线部分做好(P0→P1)。**

---

## 0. 目标与硬约束

- **硬目标(初赛必须达成)**:
  1. 路线部分先跑通:`/routes/adjust` 从纯规则 → **QwenPaw 路线 agent 驱动**(保留规则作 fallback)
  2. 后端真实调用 QwenPaw(经 `/chats`),证明「用了 QwenPaw」
  3. 评测调优 harness,产出分数图 / before-after —— 满足「智能体调优」+「开发过程证明」
- **红线**:外层不重建 QwenPaw 内层能力(memory / tool / sandbox)。
- **截图留证贯穿全程**:每个 Phase 结束补齐对应节点截图(见 §4)。

---

## 1. 数据层决策(已定,停止争论)

| 子系统 | 方案 | 理由 |
|---|---|---|
| **路线** | **结构化数据 + 路线 agent 做语义匹配**;不上向量库,也不上向量层 | 路线=过滤/排序/约束求解,向量库做不好;`candidate_selector.py` 结构化打分已验证(零向量,docstring 自述"目标不是求语义最相似") |
| **讲解 RAG** | 才用向量,且用 **pgvector**(Postgres 外挂向量列),不上独立向量库 | free-text 笔记语义检索需要;pgvector 够用 |

- **术语澄清**:pgvector = 「结构化 DB + 外挂向量层」= 队友的方案 = 我们 `config.py` 现状。**无分歧,只是叫法不同。**
- **落地动作**:
  - 路线代码 **零改动**(架构本来就对)
  - 数据保持 `data.py` 的 JSON 接口(**初赛不引入 Postgres/pgvector**,接口已留换库口子,过度工程不划算)
  - 语义模糊("想拍照出片"→ 标签)交给路线 QwenPaw agent,不需要 embedding
  - (可选,不阻塞)把 `plan/开发计划与清单.md` 里"向量数据库"措辞对齐为上表

---

## 2. 总体里程碑

| Phase | 内容 | 时间 | 对齐主线 | 截图节点 |
|---|---|---|---|---|
| **P0** | 连接基座 `qwenpaw_client` | 07/10–07/14 (W1) | — | ⑦ |
| **P1** | **路线 agent + route-adjust skill(当前优先)** | 07/14–07/20 (W2) | — | ③④⑦ |
| P2 | 文化讲解 agent + **评测/调优 harness(核心)** | 07/21–07/30 (W3) | M3 (07/30) | ⑤⑥ |
| P3 | 编排 + 护栏(ethics 4 技能)+ 多 agent 协作 | 07/31–08/06 (W4) | M4 (08/06) | ⑧ |
| P4 | 可观测 + 收尾 + 提交材料 | 08/07–08/09 (W5) | 截止 08/09 | — |

---

## 3. 分阶段

### 🟦 P0 — 连接基座(07/10–07/14)
**目标**:跑通一次 `FastAPI → QwenPaw → 真实回复`。路线 agent 依赖它,所以最先做。

任务:
- [x] ~~Console devtools 抓 `/chats` 真实请求~~ → 已用探针确认:API base `/api`;`/api/version`、`/api/agents`、`/api/chats`、`/api/chats/{id}`(本机 GET 无需鉴权);发消息子路由按 `/stream` 约定推断为 `POST /api/chats/{id}/stream`(SSE),抽成 `QWENPAW_SEND_PATH_TEMPLATE` 单一配置点,devtools 抓真请求后改一行即可
- [x] web 鉴权:本机 GET 无需;POST 可能需 → 客户端做成可选 `QWENPAW_AUTH_COOKIE`/`QWENPAW_AUTH_HEADER`(默认空,POST 401 再填)
- [x] `backend/app/agents/qwenpaw_client.py`:只读探测(version/agents/chats)+ `POST {send_path}` 收回复(SSE 解析)+ `ask()` 高层封装
- [x] `GET /api/v1/agents/ping` 返回 QwenPaw 状态(已静态验证:reachable/version/agents)
- [x] 调用 trace:`observability/trace.py` → `harness/results/traces/traces.jsonl`
- [x] 真实发一条消息端到端验证 —— `ask()` 已跑通(default agent,干净答复 + token/延迟 trace);契约 `POST /api/console/chat`(SSE,`X-Agent-Id` 头,新 session_id 自动建会话)已确认并写入 client。截图节点⑦ 待补采集

交付物:`qwenpaw_client.py`、ping 接口、一次真实调用截图。
**截图节点**:⑦ 后端连接(FastAPI 日志 `POST /chats` + curl 返回)

---

### 🟩 P1 — 路线 agent + route-adjust skill(07/14–07/20)★当前优先
**目标**:`/routes/adjust` 从纯规则升级为 **QwenPaw 路线 agent 驱动**,自然语言偏好 → 真实路线调整。

任务:
- [x] (依赖 P0)`qwenpaw_client` 已就绪
- [x] QwenPaw 建 route agent:Console 建 `路线微调`(agent-id `route`,glm-5)—— 已完成(2026-07-12);技能用 reconcile 法注册(见 `skills/README.md`,非自动发现)
- [x] 写 `route-adjust` 技能 `SKILL.md`(`skills/route-adjust/SKILL.md`):NL → 结构化意图 JSON
- [x] 后端路线 agent 封装 `backend/app/agents/route_agent.py`:agent 意图 → 叠加 Preference → 喂现成排线引擎(`construct_route` 一行不改)
- [x] 改 `/routes/adjust`:先 agent(`ROUTE_AGENT_ENABLED=true`)、失败/关闭降级规则版;响应加 `source` + trace(已静态验证 source=rules fallback)
- [x] 数据层定型:保持 `data.py` JSON,不动(见 §1)
- [x] **端到端验证**:`POST /api/v1/routes/adjust` 实测 `source=agent`(thin prompt → 结构化意图 → 排线引擎真实改路线,裁末端 + 压到 2.4km)。截图③④⑦ 待采集

交付物:`route` agent、`route-adjust` skill、agent 驱动的 `/routes/adjust`、规则 fallback。
**截图节点**:③ 建 agent、④ 写技能(SKILL.md 源码 + Console Skills 页 source=custom)、⑦ 后端连接拿真实调整

> 复用现成代码:`adjuster.py`、`candidate_selector.py`、`route_constructor.py`、`data.py` 一行不改,只在它们上面加 agent 这一层。

---

### 🟨 P2 — 文化讲解 agent + 评测/调优 harness(07/21–07/30)★核心
**目标**:第二个 agent + 用数据证明「调优过」,产出最强截图。对齐 M3。

任务:
- [ ] **★下一个立即项:route agent before/after(P1 已通,只差跑一次)** —— `ROUTE_AGENT_ENABLED=true python -m app.eval.runner --only route --run-id route-agent`(在 `backend/` 下,QwenPaw 要在跑)→ `python -m app.eval.compare --runs rules-baseline route-agent` → 截图⑥。规则 baseline 0.796 已存 `scores_rules-baseline.json`
- [ ] 调优循环:看哪条 case 分低 → 改 `skills/route-adjust/SKILL.md` / 补 `cases.json` → 换 `--run-id` 重跑 → `compare` 看涨分(分数曲线)
- [ ] ⚠️ 规则分只看结构化信号,agent 语义优势(如 r06 小众)可能不体现 → 必要时上 `rubrics/llm_judge_prompt.md` LLM-judge
- [ ] 建讲解 agent(Console 建 `文化讲解` agent-id `guide`)+ `macau-guide` skill(reconcile 法注册,见 `skills/README.md`)—— 手动待做
- [ ] `ethics/qwenpaw-skills/source-attribution/prompt.md` → SKILL.md,挂进讲解 agent
- [ ] POI 知识(`data/`)丢进 agent `file_store/`(截图⑤)
- [ ] 跑 guide 类 g01–g08(`python -m app.eval.runner --only guide --guide-agent guide`)
- [x] 建 `harness/datasets/`:`cases.json` 17 条(9 路线 + 8 讲解),从小红书真实评论/笔记取材
- [x] 建 `harness/rubrics/`:`rule_checks.md`(规则项)+ `llm_judge_prompt.md`(LLM-judge)
- [x] 写 `backend/app/eval/`:`runner.py` + `scoring.py`(跑批 + 规则打分 + 落 results);route 规则 baseline 已跑 overall **0.796**
- [x] 出图:`compare.py` 渲染自包含 HTML(SVG 柱状图 / before-after);baseline + projected 已出

交付物:讲解 agent、测试集、rubric、跑批脚本、`results/` 分数图、调优记录。
**截图节点**:⑤ 灌知识、⑥ 调优迭代(分数曲线 + before/after + SKILL.md git diff)—— **整份材料最有力**

---

### 🟧 P3 — 编排 + 护栏(07/31–08/06)
**目标**:多 agent 协作 + ethics 护栏。对齐 M4。

任务:
- [ ] 建 `需求理解` agent(若 P1/P2 未含)
- [ ] `backend/app/orchestrator/`:意图分类 → 路由到对应 agent
- [ ] 多 agent 协作:`agents chat --from-agent … --to-agent …`(需求理解 → 路线微调 → 讲解)
- [ ] `backend/app/guardrails/`:前置注入 `_ethics_base.md`;后置跑 `content-safety-review` + 事实核对 + 低置信回退
- [ ] ethics 4 技能既挂内层 agent、也作外层 hook(两处都留截图)

交付物:orchestrator、guardrails、多 agent 协作链路。
**截图节点**:⑧ 多 agent 协作 + 护栏拦截记录

---

### 🟥 P4 — 可观测 + 收尾 + 提交材料(08/07–08/09)
- [ ] `backend/app/observability/`:每次 QwenPaw 调用 trace 落库(对齐 `ethics/实施清单.md §3`),出调用链路图
- [ ] 知识 pipeline 收尾:`rag/ingest.py` 真接 embedding → 讲解 agent memory
- [ ] 整理提交三件套:策划书(引用评测数据)、开发过程证明(截图+视频)、团队视频(≤3min)
- [ ] 最终端到端 Demo:前端 → FastAPI → QwenPaw → 路线/讲解

---

## 4. 截图采集清单(贯穿全程,对应「开发过程证明」)

| # | 关键节点 | 截什么 | 状态 |
|---|---|---|---|
| ① | 基础部署 | Console 首页 + `qwenpaw --version` + `qwenpaw app` 进程 | ⬜ 待采 |
| ② | 模型接入 | Console → Settings → Models,provider 已启用(key 打码) | ⬜ 待采 |
| ③ | 创建 agent | Edit Agent 页(id/name/model/挂技能)+ `qwenpaw agents list` | ✅ 已采(2026-07-12) |
| ④ | 写技能(核心开发证据) | Console Skills 页(custom enabled)+ SKILL.md 源码 + `skills list` source=custom | ✅ 已采(route-adjust/macau-guide source=Custom) |
| ⑤ | 灌知识(RAG) | agent `file_store/` POI 数据 + Console 对话引用具体景点 | ⬜ 待采(P2) |
| ⑥ | 调优迭代 | 分数曲线 + before/after + SKILL.md git diff | ⬜ 待采(P2,下一个立即项) |
| ⑦ | 后端连接 | FastAPI 日志 `POST /api/console/chat` + curl 返回 `source=agent` | ✅ 已采(2026-07-12) |
| ⑧ | 多 agent 协作 | `agents chat --from … --to …` 过程 | ⬜ 待采(P3) |

> 再录 1–2 分钟屏幕视频:Console 建 agent → 装技能 → 对话 → 前端调用,覆盖大半节点。截图存 `harness/results/screenshots/`,命名带节点编号。

---

## 5. 关键技术决策

- **连接**:FastAPI → QwenPaw `/chats`(REST),非直连 DashScope。这是「真用了 QwenPaw」的判定线。
- **鉴权**:QwenPaw web 有登录(`qwenpaw auth`);后端用专用 web 账号,token 进 `.env`。
- **路线数据**:结构化 JSON(`data/`),初赛不换 Postgres/pgvector(见 §1)。
- **路线 agent 输出**:严格 JSON → 直接喂 `construct_route`,agent 不碰排线算法。
- **评测打分**:规则项为主(零成本可重复),LLM-judge 为辅(便宜模型,测试集 ≤20 条)。
- **技能分发**:开发期文件夹批量丢 `skill_pool/`;交付/演示再考虑 `plugin install` 打包。

---

## 6. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| `/chats` send/stream 子路由没文档 | P0 卡住 | Console devtools 抓真实请求;不行读 `qwenpaw chat` CLI 源码 |
| web 鉴权 token 机制不明 | 后端连不上 | P0 第一步先打通;规则版 `adjuster.py` 留作 fallback |
| agent 不按 JSON schema 输出 | 路线解析失败 | SKILL.md 强约束 + few-shot;解析失败降级回规则版 |
| LLM-judge 跑批 token 成本 | P2 预算 | 规则项为主 + 便宜模型;测试集 ≤20 条 |
| QwenPaw 本地不稳定 | 演示翻车 | 关键 agent 留 fallback;演示用录屏备份 |
| 时间紧(4.5 周) | 做不完 | P0/P1(路线)优先;P3 护栏可只做 2 个核心技能;P4 材料提前写 |
