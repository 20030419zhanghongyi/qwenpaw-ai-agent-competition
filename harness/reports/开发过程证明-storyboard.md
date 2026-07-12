# 开发过程证明 —— 截图 / 文字 / 图表 分镜册

> 对应初赛提交要求三件套之一：**「开发过程证明（截图 / 文字 / 图表 / 视频），展示在关键节点使用 QwenPaw 的情况」**。
> 本文是**采集分镜 + 预写说明文字 + 证据映射**：你按表截屏、把图丢进 `harness/results/screenshots/`，说明文字基本可直接贴进提交材料。
> 维护人：队长。状态截至 **2026-07-10**。

---

## 0. 一句话判定线

> **「我们用了 QwenPaw」的判定线 = 后端真实调用过 QwenPaw 的 `/api/console/chat`，且有 trace 落盘为证。这条已经达成（见 §1 第 7 项）。** 截图是把这件事「可视化」给评委看，不是从零证明。

---

## 1. 已经自动生成的证据（无需截图，直接可引用）

这些是代码/运行时**自动产出**的硬证据，提交材料里直接贴文件路径 + 关键数字即可，比截图更可信。

| # | 证据 | 文件 / 来源 | 关键数字 / 内容 | 证明什么 |
|---|---|---|---|---|
| A1 | **真实 QwenPaw 调用 trace** | `harness/results/traces/traces.jsonl` | `kind:"qwenpaw.ask"`，agent=default，回复「澳门历史城区的心脏，葡式波浪纹石铺广场。」，latency 3946ms，tokens {prompt 11031 / completion 29 / total 11060} | 后端经 `/api/console/chat` 真实拿到 Qwen 模型回复 ——「真用了 QwenPaw」 |
| A2 | **连接基座探针** | `GET /api/v1/agents/ping` | `reachable:true`，`qwenpaw_version:1.1.12.post3`，agents=[default, QwenPaw_QA_Agent_0.2] | QwenPaw 实例可达、版本、已注册 agent |
| A3 | **评测基线（真实跑出）** | `harness/results/scores_rules-baseline.json` | route 类 overall **0.796**（n=9） | 有可重复的量化评测，不是主观描述 |
| A4 | **调优目标（投影）** | `harness/results/scores_demo-after(PROJECTED).json` + `compare_rules-baseline_vs_demo-after(PROJECTED).html` | route 投影 **1.0** | ⚠️ **当前是 PROJECTED（目标），不是实测**；route agent 启用后重跑即变实测 before/after |
| A5 | **路线微调技能源码** | `skills/route-adjust/SKILL.md` | 含职责定义 + few-shot | 「会写 QwenPaw 技能」的源码级证据 |
| A6 | **路线 agent 封装 + 降级** | `backend/app/agents/route_agent.py`、`backend/app/features/routes/api.py` | `/routes/adjust` 先 agent 后规则 fallback | agent 接入工程化、有兜底 |
| A7 | **POI 知识库** | `data/pois.json` | 339 POI（14 文化富化 + 325 地理编码），district 统一官方堂区 | 灌给讲解/路线 agent 的知识基础 |

> **薄弱用例（最有说服力的「调优前」痛点）**：基线里 `r01=0.333`（少走路+裁末端都没做到）、`r07=0.5`（时长没改）、`r04/r09=0.667`（加美食/兴趣点没命中）。这 4 条**正是规则版做不到、要靠 route agent 修的**——是 before/after 故事的核心弹药。

---

## 2. 八节点截图分镜（对应 `harness/plan.md §4`）

> 列：**节点 / 截什么 / 捕获步骤 / 预写说明文字（可直接贴） / 存放路径 / 状态**。
> 命名约定：`screenshots/节点编号_简述.png`（如 `03_agents-list.png`）。

### ① 基础部署 ✅ 可立即截
- **截**：QwenPaw Console 首页 + 终端 `qwenpaw --version`（输出 `1.1.12.post3`）+ `qwenpaw app` 进程（或 `~/Desktop/启动QwenPaw.sh` 启动后 8088 端口）。
- **步骤**：`/opt/anaconda3/envs/qwenpaw/bin/qwenpaw --version`；浏览器开 `http://127.0.0.1:8088/`。
- **说明文字**：QwenPaw 工作站（v1.1.12.post3）已本地部署并运行于 8088，后端探针 `/api/v1/agents/ping` 返回 `reachable:true`。
- **存**：`01_deploy.png`
- **状态**：✅ 自动证据已有（A2）；截图补充可视化。

### ② 模型接入 ✅ 可立即截
- **截**：Console → Settings → Models，provider 列表（Aliyun token plan 启用；key 打码）。
- **说明文字**：模型 provider 已配置（百炼 Aliyun token plan；deepseek/glm 用于测试），路线/讲解 agent 调用 qwen-plus 等模型。
- **存**：`02_models.png`

### ③ 创建 agent 🟡 部分（route/guide 待建）
- **截**：Create New Agent 页 + 终端 `qwenpaw agents list`。
- **说明文字**：在 QwenPaw 注册项目所需 agent。当前已有 `default`、`QwenPaw_QA_Agent_0.2`；**待建 `route`（路线微调）、`guide`（文化讲解）** 两个核心 agent（见 §4 待补）。
- **存**：`03_agents-list.png`、`03_create-route.png`（建好后补）
- **状态**：🟡 现有 agent 可截；route/guide 建好后再补一张。

### ④ 写技能（核心开发证据）⭐ ✅ 可立即截
- **截**：Console → Skills 页（`route-adjust` 显示 custom/enabled）+ `skills/route-adjust/SKILL.md` 源码截图 + 终端 `qwenpaw skills list`（source=custom）。
- **说明文字**：以 QwenPaw **技能（SKILL.md）**形式定义路线微调能力——把「不想太累 / 加个拍照点 / 别绕路」等自然语言翻译成结构化偏好变更，输出严格 JSON；技能含 few-shot 样本。这是「在 QwenPaw 上做开发」最直接的源码证据。
- **存**：`04_skill-console.png`、`04_skill-source.png`
- **状态**：✅ 技能源码已就位（A5）；Console 启用后截。

### ⑤ 灌知识（RAG）🟡 数据已备，挂载待做
- **截**：agent `file_store/` 内的 POI 数据 + Console 对话中 agent 引用具体景点（如正确说出议事亭前地碎石花纹）。
- **说明文字**：把 339 条 POI 结构化知识（含历史/建筑/故事）作为讲解依据挂给 guide agent，使其回答有据、可标来源。
- **存**：`05_knowledge.png`
- **状态**：🟡 `data/pois.json` 已备（A7）；挂进 agent file_store + 对话验证待做。

### ⑥ 调优迭代 ⭐ 🟡 基线已实，after 待实测
- **截**：分数柱状图（baseline 0.796 vs after）+ 典型 case before/after（r01 0.333→1.0）+ `SKILL.md` 的 git diff。
- **说明文字**：建立 17 条源自小红书真实评论/笔记的评测集（9 路线 + 8 讲解），规则版基线 route=0.796；针对薄弱用例（少走路/改时长/加美食点）迭代技能与 prompt，**实测 after 分数 + 典型 case 前后对比**展示调优效果。
- **存**：`06_eval-chart.png`、`06_case-diff.png`、`06_skill-diff.png`
- **状态**：🟡 基线图已有（`chart_rules-baseline.html`）；**实测 after 需 route agent 启用后重跑**（当前 `scores_demo-after(PROJECTED).json` 是投影目标，提交前必须换成实测，否则会虚标）。

### ⑦ 后端连接 ✅ 可立即截（最强证据）
- **截**：FastAPI 终端日志（`POST /api/v1/routes/adjust` 或 `/agents/ping`）+ `curl` 返回 + 前端拿到真实结果。
- **说明文字**：FastAPI 后端经 QwenPaw `/api/console/chat`（SSE）拿到真实模型回复并落 trace（含延迟与 token 用量），证明调用链 `前端 → FastAPI → QwenPaw → Qwen 模型` 全通。
- **存**：`07_backend-log.png`、`07_curl-reply.png`
- **状态**：✅ trace 已落盘（A1）；截图补可视化。**这一节是整份材料最有力的一张**，优先截。

### ⑧ 多 agent 协作 ⬜ 待做（P3）
- **截**：终端 `qwenpaw agents chat --from-agent … --to-agent …` 过程（需求理解 → 路线微调 → 讲解）。
- **说明文字**：多 agent 经 QwenPaw `agents chat` 协作完成「理解需求 → 微调路线 → 生成讲解」链路。
- **存**：`08_multi-agent.png`
- **状态**：⬜ P3 编排上线后截；初赛若来不及可降级（前 7 节已足够）。

---

## 3. 1–2 分钟录屏脚本（覆盖大半节点）

> 一条屏录覆盖 ①②③④⑦，比 8 张静态图更省评委时间。建议脚本：

1. (0:00) 终端 `qwenpaw --version` → 1.1.12.post3；`curl /api/v1/agents/ping` → reachable（**①⑦**）
2. (0:15) 切 Console：首页 → Settings/Models（key 打码）（**①②**）
3. (0:30) Skills 页：点亮 `route-adjust`（custom）→ 侧栏打开 `SKILL.md` 源码（**④**）
4. (0:50) agents list / Create Agent 页（**③**）
5. (1:05) 终端 `curl -X POST /api/v1/routes/adjust ...`（或前端点一次微调）→ 看返回 + FastAPI 日志（**⑦**）
6. (1:30) 打开 `traces.jsonl` 末尾，指给镜头看那条 `qwenpaw.ask`（**⑦ 收尾，点睛**）

存 `screenshots/dev-walkthrough.mp4`。

---

## 4. 提交前必做（把「投影」换成「实测」）

当前最强的调优证据（⑥）里，**after=1.0 是 PROJECTED**。提交前必须：

1. 在 QwenPaw 建 `route` agent（`qwenpaw agents create --name "路线微调" --agent-id route`）并启用 `route-adjust` 技能。
2. `.env` 设 `ROUTE_AGENT_ENABLED=true`。
3. 重跑评测 → 产出**实测** `scores_route-agent.json`，替换投影图。
4. 若实测未达 1.0，据薄弱 case 迭代 `SKILL.md`，留 git diff 作调优证据（这正是「智能体调优」的本来面目，反而更真实）。

> 同理 `guide` 类 8 条（g01–g08）目前 `by_category.guide=null`（guide agent 未建）。建好 guide agent 后跑一次，补齐讲解侧分数。

---

## 5. 清单（提交前过一遍）

- [ ] ①②③④⑦ 截图入 `screenshots/`（⑤⑥⑧ 视进度）
- [ ] 1–2 分钟录屏
- [ ] ⑥ 的 after 换成实测（route agent 启用后重跑）
- [ ] guide 类评测补跑
- [ ] 把 §1 自动证据表的关键数字写进策划书「开发过程」一节
