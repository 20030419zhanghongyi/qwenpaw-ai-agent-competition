# 澳跡同行 Macau StoryWalk — 功能驱动开发清单（Feature-Driven）

> 基于 `plan/report ver4.5.docx`（概念设计书 §3 功能设计 10 大功能 + §3.2 六层架构 / 六 Agent）。
> **本版定位**：从「按阶段开发（先后端、再前端）」改为「**按功能切片开发（前后端同步）**」。
> 起算 2026-07-14；初赛 🚩 2026-08-09。维护人：队长。
> 旧清单见 `plan/开发计划与清单.md`（按 Phase 1–6 组织，仍可作为时间线参考）。

---

## 0. 为什么改成「功能驱动」

旧模式（阶段驱动）：后端把所有 API 做完 → 再交前端。问题：① 前端干等；② 后端做了很多前端用不上的字段；③ 联调集中到末尾，风险大。

新模式（功能驱动 / vertical slice）：**一个用户功能 = 后端 + 前端 + 契约 + 联调验收**，作为一个最小可交付单元。前后端同时开工，靠 **API 契约** 对齐：

```
每个功能切片（Feature Slice）
  ├─ 契约（OpenAPI：路径 / 请求 / 响应 / 错误码）  ← 先定，双方一起评审
  ├─ 后端任务（实现 endpoint + 数据 + agent）      ← 可独立提交
  ├─ 前端任务（页面 / 交互 / 接 mock）             ← 后端没好时先用 mock，好了切真实
  └─ 联调验收（端到端跑通一条用户路径）
```

**协作约定**
- **契约先行**：开功能前，先把该功能的 endpoint 写进本文档「契约」一栏 + `/docs` Swagger，双方以它为准；改契约要走变更。
- **前端不阻塞后端**：后端没上线前，前端按契约用 **mock（MSW / 本地 json）**；后端 ready 后改一行 baseURL 切换。
- **功能分支**：`feat/<功能名>`（如 `feat/voice-guide`），联调通过再合 `master`。
- **每功能一个 Demo 卡点**：合入前在 Web 上能看到这一条用户路径走通。

---

## 1. 当前后端能力盘点（已读码核实，截至 2026-07-14）

### 1.1 已实现 Endpoint（真实可用）

| 功能域 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 健康 | GET | `/api/v1/health` | API + DB 状态 |
| 用户 | POST | `/api/v1/users` | ⚠️ **内存存储** `_INMEMORY`，未落库 |
| 用户 | GET | `/api/v1/users/{id}` | ⚠️ 内存 |
| 用户 | PUT | `/api/v1/users/{id}/preferences` | ⚠️ 内存 |
| POI | GET | `/api/v1/pois`、`/pois/nearby`、`/pois/{id}` | ✅ PostGIS 空间查询 |
| 路线 | GET | `/api/v1/routes`、`/routes/{id}` | ✅ 模板库（6 模板 / 38 节点）|
| 路线 | POST | `/api/v1/routes/match` | ✅ 模板召回 + 规则约束排序 |
| 路线 | POST | `/api/v1/routes/adjust` | ✅ 自然语言微调（route agent）|
| 行程 | POST | `/api/v1/trips`、`/trips/{id}/checkins` | ✅ Trip/打卡 落库 |
| 行程 | GET | `/api/v1/trips/{id}`、`/{id}/progress` | ✅ |
| 历史 | GET | `/api/v1/users/{id}/trips` | ✅ |
| 收藏 | POST/DELETE/GET | `/api/v1/users/{id}/favorites/pois` | ✅ |
| 反馈 | POST/GET | `/api/v1/trips/{id}/feedback` | ✅ |
| 意图 | POST | `/api/v1/intent/parse` | ✅ 需求理解 agent（NL→结构化）|
| 审核 | POST | `/api/v1/review/content` | ✅ 独立审核 agent |
| 讲解 | POST | `/api/v1/guide/generate` | ✅ 文化讲解 agent + pgvector RAG |
| 拍照 | POST | `/api/v1/guide/photo` | ✅ Qwen-VL + 图像脱敏 + 讲解 |
| 探测 | GET | `/api/v1/agents/ping` | ✅ QwenPaw 连通性 |

### 1.2 Agent 落地状态（设计书 §3.2 六 Agent）

| # | 设计书 Agent | 实现 | 评测 | 备注 |
|---|---|---|---|---|
| 1 | 用戶需求理解 | ✅ `intent_agent` | ✅ | intent eval |
| 2 | 路線配對與微調 | ✅ `route_agent` | ✅ | before/after 0.796→0.963 |
| 3 | 文化講解 | ✅ `guide_agent` | ✅ | pgvector RAG + guide→reviewer 管道 |
| 4 | 圖像識別講解 | ✅ `photo_agent` | ✅ | view_image 多模态 + 脱敏 |
| 5 | 反饋優化 | ✅ `reviewer_agent` | ✅ | content-safety-review |
| 6 | **多語言生成** | ⚠️ **未独立成 agent** | — | 现状：guide/photo 带 `language` 参数局部多语；**无粤语专项、无统一多语层** |

### 1.3 基础设施（已就绪）
- ✅ 统一库（PostGIS + pgvector）容器化，341 POI / 6 路线模板 / 339 RAG embedding
- ✅ RAG 语义检索（HNSW），guide 端到端验证可用
- ✅ 配置层 `config.py` **已预留** `qwen_tts_model` / `tts_api_key` / `weather_api_key` / `crowd_api_key` / `amap_*` / `jwt_secret` —— 但**尚无对应业务代码**

---

## 2. 功能切片总表（10 功能 × 后端状态 × 优先级）

> 状态：✅ 后端就绪 ｜ 🟡 部分就绪需补 ｜ ❌ 后端缺失待建 ｜ 🔵 复赛阶段
> 优先级：P0 初赛核心闭环必须 ｜ P1 初赛加分 ｜ P2 复赛

| # | 功能（设计书） | 后端状态 | 后端待办要点 | 优先级 |
|---|---|---|---|---|
| F1 | 注册登录 + 语言选择 | ✅ | 用户/偏好落库 + 极简 JWT 登录已落地（2026-07-14）；语言贯穿待后续 | P0 |
| F2 | 用户偏好输入 | ✅ | — | P0 |
| F3 | 个性化路线推荐 | ✅ | （可选）天氣/人流接入后增强微调 | P0 |
| F4 | 地图路线展示 + 调整 | ✅ | `POST /routes/walk-path` 返回高德逐段步行路径、时间与 polyline | P0/P1 |
| F5 | 位置触发式讲解 | ✅ | `POST /guide/trigger`（lat/lng→最近文化节点→确认后讲解）| P0 |
| F6 | 拍照识别 + 即时讲解 | ✅ | 低置信明确回退为重拍/手选，不生成不确定讲解 | P0 |
| F7 | 语音导览 | ✅ | `POST /guide/tts`：Qwen3 TTS + 私有 OSS 短期 URL（部署需配置密钥）| P0 |
| F8 | 多模态文化内容生成 | 🔵 | 图片/视觉卡片生成 | P2 |
| F9 | 个性化明信片 + 旅行回忆 | 🔵 | 打卡已有；明信片合成 + 文案 + 串联 | P2 |
| F10 | 个人中心 + 历史行程 | 🟡 | 历史/收藏/反馈已就绪；缺明信片入口 | P0(部分)/P2 |

**初赛（8/9）核心闭环红线**：F1 → F2 → F3 → F4 → F5 → F6 → F7 → F10。F8/F9 降级复赛。

---

## 3. 各功能详拆（Vertical Slice）

### 🟦 F1 注册登录 + 语言选择（P0）— ✅ 后端完成（2026-07-14）
**设计书**：注册/登录保存历史；支持 英/简中/繁中/葡 四语，界面随语言切换。
- **后端状态**：✅ 用户/偏好落 PostgreSQL + 极简 JWT 登录已落地。旧 `app/api/users.py`（`_INMEMORY`）已删除。
- **契约（已实现）**
  - `POST /api/v1/users/register` { user_id?, name?, language } → { user_id, token, user }（user_id 不填则后端生成 `u_` 前缀；重复 409；非法语言 422）
  - `POST /api/v1/users/login` { user_id } → { user_id, token }（未注册 404；demo 不设密码，见伦理「最小必要」）
  - `GET /api/v1/users/me`（Bearer）→ { user }（缺/坏 token 401）
  - `GET /api/v1/users/{user_id}` → { user }（404 if 不存在）
  - `PUT /api/v1/users/{user_id}/preferences` { Preference } → { status, user_id, preference }（整体 JSON 落库；用户不存在则 upsert 创建）
- **后端待办**
  - [x] User + Preference 落 PostgreSQL（迁移 `20260714_01` 加 `name`+`preference` JSON 列；`features/users/repository.py`）
  - [x] 极简登录：JWT（`core/security.py`，HS256 / 7 天有效期，用既有 `jwt_secret`）
  - [x] `language` 存用户表，与 `preference.language` 同步
  - [ ] **语言贯穿**：guide/route/intent 响应暂按请求参数 `language`，尚未自动读取已登录用户的 `user.language`（后续接入 `current_user` 依赖即可）
- **前端待办**：语言选择页 + i18n 接入 + 注册/登录页（契约已定，可并行开工）
- **验收**：✅ 注册→DB 有行→重新 login→`/me` 仍带偏好（DB 持久化铁证，已 e2e 验证）；切语言 = 改 preference.language 后顶层 language 同步。

### 🟩 F2 用户偏好输入（P0）— ✅ 后端就绪
- **契约**：`PUT /api/v1/users/{id}/preferences`；`POST /api/v1/intent/parse`（自然语言→结构化）
- **后端待办**：无（F1 落库后顺手把偏好一起落库）
- **前端待办**：偏好输入页（选择题/勾选框为主）+ 自然语言输入框（走 intent/parse）
- **验收**：结构化偏好 + 自然语言两种入口都能产出同一份 Preference。

### 🟨 F3 个性化路线推荐（P0）— ✅ 后端就绪
- **契约**：`POST /api/v1/routes/match`（结构化偏好→模板+规则）；`POST /api/v1/routes/adjust`（自然语言微调）
- **后端待办**：无（天氣/人流数据源到位后再增强）
- **前端待办**：路线结果页（地图+行程卡片双视图）+ 「推荐理由/相似替换点」展示
- **验收**：复现设计书 §5 对话 A/B/C（半天+拍照+不想太累→配对+微调+理由）。

### 🟧 F4 地图路线展示 + 调整（P0/P1）
**设计书**：地图标节点+步行顺序+起终点；行程卡片含停留/步行时间；用户可删点/加点/减步行→重算。
- **后端状态**：✅ `POST /api/v1/routes/walk-path` 接收调整后有序 POI 列表，调用高德 direction v5 并返回逐段距离、时间和 polyline；高德不可用时明确 503，不伪造估算。
- **前端待办**：地图组件画 polyline + marker + 起终点；调点 UI（删/加/减步行）→ 调后端重算
- **验收**：删一个点后，地图连线与「预计步行」同步更新；距离不再是大致估算。

### 🟥 F5 位置触发式讲解（P0）— ✅ 后端就绪
**设计书**：靠近文化节点→提醒→用户确认→文字/语音讲解。M4（8/6）核心，初赛红线。
- **后端状态**：✅ `POST /guide/trigger` 复用 PostGIS nearby 查询，默认 80m 命中最近 POI；同一匿名会话同一 POI 10 分钟内只提示一次。
- **契约（已实现）**
  - `POST /api/v1/guide/trigger` `{ latitude, longitude, session_id, radius_m?, language }` → `{ triggered, reason?, poi?, distance_m?, prompt?, guide_request? }`
  - 只探测并返回确认提示；用户确认后，前端携带 `guide_request` 调既有 `POST /api/v1/guide/generate`，不在未确认时调用 Agent。
- **后端待办**：无（TTS 仍由 F7 承接）。
- **前端待办**：定位上报 + 围栏判定（也可前端做）+ 「叮～你已靠近 XX，要听讲解吗？」弹层
- **验收**：模拟进入「疯堂斜巷」围栏 → 推送讲解成功（设计书 §5 场景二）。

### 🟪 F6 拍照识别 + 即时讲解（P0）— ✅ 后端就绪
- **契约**：`POST /api/v1/guide/photo`（multipart 图片 → 识别 + 定位 + 讲解，已含 EXIF/人脸脱敏）
- **后端加固**：✅ 低置信度（<0.6）、无标准 POI 或 Agent 失败时返回 `uncertain`、重拍/手选动作；不触发 RAG 讲解。
- **前端待办**：拍照/上传页 + 识别结果讲解卡 + 低置信态引导重拍
- **验收**：拍葡式花砖→识别 Azulejo + 讲解（设计书 §5 场景）。

### 🟫 F7 语音导览（P0）— ✅ 后端就绪
**设计书**：讲解文本→语音；普通话/粤语/英/葡；粤语用本地化口吻非直译。M4（8/6）**必做**。
- **后端状态**：✅ `POST /api/v1/guide/tts` 固定映射普通话、粤语、英语、葡语音色，生成后上传私有 OSS 并返回短期 URL；配置或外部服务不可用时返回 503。
- **前端待办**：播放器组件；「确认后播放」（不做持续陪伴式，控成本）
- **验收**：到达节点→生成讲解→播放普通话+粤语各一（设计书 M4 验收）。

### 🟦 F8 多模态文化内容生成（P2 / 复赛）
- **状态**：🔵 缺失（设计书明示「早期可优先静态图/视觉卡片，视频留复赛」）
- **后端待办（复赛）**：`POST /guide/illustration` 历史场景插图 / 视觉讲解卡（须标「AI 示意」非史料，伦理 §8.2）
- **前端待办（复赛）**：讲解卡内嵌生成图

### 🟩 F9 个性化明信片 + 旅行回忆（P2 / 复赛）
- **状态**：🔵 打卡（checkin）已有；**明信片合成/文案/串联全缺**。
- **契约（建议，复赛）**
  - `POST /api/v1/postcards` { trip_id, poi_id, photo } → { postcard_url, caption }（合影走脱敏）
  - `GET /api/v1/trips/{id}/postcards` → 明信片列表（按游览顺序）
  - `POST /api/v1/trips/{id}/memory` → 串联旅行回忆（图集/短视频）
- **后端待办（复赛）**：明信片版式合成 + QwenPaw 文案（时间戳/地理戳/地点名）+ 回忆串联
- **前端待办（复赛）**：明信片展示/分享/回忆回放

### 🟨 F10 个人中心 + 历史行程（P0 部分 / P2）
- **状态**：🟡 历史行程/收藏/反馈 ✅；缺明信片入口（依赖 F9）、偏好回看。
- **后端待办**：F1 落库后补「个人资料回看」；明信片入口等 F9
- **前端待办**：个人中心页（历史/收藏/反馈/明信片入口）

---

## 4. 后端专项：初赛还剩什么（🔥 用户核心问题）

> 结论：核心数据/路线/讲解/拍照/位置触发/步行路径/语音导览链路均已完成；当前后端重点转为真实外部凭据 smoke test 与前端联调。

### 🔥 P0 — 初赛（8/9）后端状态

核心后端接口已实现；部署前需配置高德 Web 服务、DashScope/Qwen TTS、私有 OSS 与 QwenPaw，并完成真实 smoke test。

### 🟡 P1 — 初赛加分 / 加固
- B6 粤语讲解文案专项（guide prompt 分语种，配合 B3 粤语 TTS）
- B7 审计日志去标识化 ✅（PostgreSQL 30 天留存 + JSONL 哈希/长度 metadata）

### 🔵 P2 — 复赛
- B8 天气/人流/节庆数据接入 → route/adjust 增强微调因子（需数据源）
- B9 明信片合成 + 文案 + 旅行回忆串联（F9）
- B10 多模态历史插图/视觉卡（F8）
- B11 多语言统一 agent 化（设计书第 6 个 agent，现状散在 guide/photo）

### ✅ 后端「已Done、别重复造」清单（给前端/队友）
- POI / 路线 / 行程 / 打卡 / 收藏 / 反馈 全链路落库 ✅
- 路线 match（模板+规则）+ adjust（agent）✅
- 文化讲解（RAG）+ 拍照识别（多模态+脱敏）✅
- 位置触发（PostGIS nearby + 会话级防重复提示）✅
- 5/6 Agent 已接入 QwenPaw 并有评测 ✅
- 统一库容器化一键起 ✅

---

## 5. 并行开发建议排期（功能切片，2 人/多人在场可并行）

> 原则：**契约一旦写定，后端与前端同功能并行**。下面按「可立即并行」分组。

**第一批（本周可开，契约易定）**
- F5 前端定位+确认弹层 — 调 `/guide/trigger`，确认后复用 `/guide/generate`
- F7 前端播放器 — 调 `/guide/tts`，使用短期 `audio_url`

**第二批**
- F4 前端地图 polyline — 调 `/routes/walk-path`
- F10 个人中心收口

**第三批（复赛）**
- F8 / F9 / B8 天气人流 / B11 多语 agent

---

## ✅ 总进度看板（功能驱动）

- [x] F1 注册登录+语言（后端 B1 落库 + JWT 完成 ✅ 2026-07-14；语言贯穿待后续）
- [x] F2 偏好输入
- [x] F3 路线推荐
- [x] F4 地图+调整（后端 walk-path 就绪；前端待接地图）
- [x] F5 位置触发讲解（B2：PostGIS nearby + 会话级防重复提示；确认后复用 guide/generate）
- [x] F6 拍照识别（低置信回退 + POI 手选入口）
- [x] F7 语音导览（后端 Qwen3 TTS + OSS 就绪；前端待接播放器）
- [ ] F8 多模态生成（复赛）
- [ ] F9 明信片+回忆（复赛）
- [~] F10 个人中心（待 F1 落库 + F9）

---

*— 清单版本 v1.0（feature-driven）| 2026-07-14 | 基于 report v4.5 + 代码核实 | 与 `开发计划与清单.md`（phase 版）互补 —*
