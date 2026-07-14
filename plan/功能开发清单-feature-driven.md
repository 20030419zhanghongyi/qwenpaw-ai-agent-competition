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
| F4 | 地图路线展示 + 调整 | 🟡 | amap 步行 polyline / 步行时间 / 距离重算 | P0/P1 |
| F5 | 位置触发式讲解 | ❌ | `POST /guide/trigger`（lat/lng→最近文化节点→讲解）| P0 |
| F6 | 拍照识别 + 即时讲解 | ✅ | （可选）低置信度「未能确定」回退显式化 | P0 |
| F7 | 语音导览 | ❌ | `POST /guide/tts`（CosyVoice，含粤语）| P0 |
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
- **后端状态**：🟡 路线节点/坐标/顺序都有；`walk_distance_km` 字段存在（`models/route.py:24`）但为模板静态值；**无道路网步行距离/polyline/步行时间动态计算**；用户「加点」后距离/用时不会精确重算。
- **契约（建议）**
  - `GET /api/v1/routes/{id}/walk-path` → { polyline, segments:[{from,to,walk_m,walk_min}] }
  - 或在 `/routes/adjust` 响应里补 `polyline` + 逐段 `walk_min`
- **后端待办**
  - [ ] 接高德 Web 服务 **direction（步行）**：节点两两步行距离/时间 + polyline（`amap_web_service_key` 已配置占位）
  - [ ] route_constructor / adjust 拿真实步行距离重算总时长与「少走路」约束
  - [ ] 返回 polyline 供前端地图画线
- **前端待办**：地图组件画 polyline + marker + 起终点；调点 UI（删/加/减步行）→ 调后端重算
- **验收**：删一个点后，地图连线与「预计步行」同步更新；距离不再是大致估算。

### 🟥 F5 位置触发式讲解（P0）— ❌ 后端缺失
**设计书**：靠近文化节点→提醒→用户确认→文字/语音讲解。M4（8/6）核心，初赛红线。
- **后端状态**：❌ 有 `GET /pois/nearby`（PostGIS 缓冲），但**无「位置→讲解」一体化触发端点**。
- **契约（建议）**
  - `POST /api/v1/guide/trigger` { latitude, longitude, radius_m?, language } → { triggered: bool, poi, narration, confidence }
  - 逻辑：PostGIS 找半径内最近文化节点 → 命中则复用 guide/generate 出讲解；未命中 `triggered=false`
- **后端待办**
  - [ ] 新建 `POST /guide/trigger`：nearby 查询 + guide 复用 + 阈值控制（防抖：同一 POI 短时不重复触发）
- **前端待办**：定位上报 + 围栏判定（也可前端做）+ 「叮～你已靠近 XX，要听讲解吗？」弹层
- **验收**：模拟进入「疯堂斜巷」围栏 → 推送讲解成功（设计书 §5 场景二）。

### 🟪 F6 拍照识别 + 即时讲解（P0）— ✅ 后端就绪
- **契约**：`POST /api/v1/guide/photo`（multipart 图片 → 识别 + 定位 + 讲解，已含 EXIF/人脸脱敏）
- **后端待办（可选加固）**
  - [ ] 低置信度（<0.6）显式返回「未能确定」+ 重拍/手选选项（伦理透明度，设计书 §8.2）
- **前端待办**：拍照/上传页 + 识别结果讲解卡 + 低置信态引导重拍
- **验收**：拍葡式花砖→识别 Azulejo + 讲解（设计书 §5 场景）。

### 🟫 F7 语音导览（P0）— ❌ 后端缺失
**设计书**：讲解文本→语音；普通话/粤语/英/葡；粤语用本地化口吻非直译。M4（8/6）**必做**。
- **后端状态**：❌ 无任何 TTS 代码（`qwen_tts_model=cosyvoice-v1` / `tts_api_key` 仅配置占位）。
- **契约（建议）**
  - `POST /api/v1/guide/tts` { text, language, voice? } → { audio_url } （或直接流式 audio）
  - 可与 `/guide/generate` 合并：加 `with_audio=true` 一并返回 `audio_url`
- **后端待办**
  - [ ] 接 CosyVoice / Qwen-TTS：文本→音频（落 OSS/本地静态目录）→ 返回 URL
  - [ ] 多音色：普通话 / 粤语（`yue`）/ 英 / 葡 映射
  - [ ] 与 guide 生成联动：讲解出来即可播放
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

> 结论：**后端并非「全部做完」**。核心数据/路线/讲解/拍照链路 ✅；但「行走中」的三块（位置触发、语音、地图步行路径）+ 用户落库是初赛真缺口。

### 🔥 P0 — 初赛（8/9）前必须补的后端

| 缺口 | 功能 | 工作量 | 依赖 |
|---|---|---|---|
| **B1 用户落库 + 极简登录** | F1 | 中 | 无（ORM 已有，接 repository）|
| **B2 `POST /guide/trigger` 位置触发讲解** | F5 | 小 | 复用 pois/nearby + guide/generate |
| **B3 `POST /guide/tts` 语音导览（含粤语）** | F7 | 中 | CosyVoice/Qwen-TTS key + 存储 |
| **B4 高德步行 direction：polyline + 步行时间/距离** | F4 | 中 | 高德 Web key |

### 🟡 P1 — 初赛加分 / 加固
- B5 photo 低置信度「未能确定」显式回退（伦理透明度，F6）
- B6 粤语讲解文案专项（guide prompt 分语种，配合 B3 粤语 TTS）
- B7 审计日志去标识化（`observability/trace.py` 已有雏形，补全，伦理 §8.3）

### 🔵 P2 — 复赛
- B8 天气/人流/节庆数据接入 → route/adjust 增强微调因子（需数据源）
- B9 明信片合成 + 文案 + 旅行回忆串联（F9）
- B10 多模态历史插图/视觉卡（F8）
- B11 多语言统一 agent 化（设计书第 6 个 agent，现状散在 guide/photo）

### ✅ 后端「已Done、别重复造」清单（给前端/队友）
- POI / 路线 / 行程 / 打卡 / 收藏 / 反馈 全链路落库 ✅
- 路线 match（模板+规则）+ adjust（agent）✅
- 文化讲解（RAG）+ 拍照识别（多模态+脱敏）✅
- 5/6 Agent 已接入 QwenPaw 并有评测 ✅
- 统一库容器化一键起 ✅

---

## 5. 并行开发建议排期（功能切片，2 人/多人在场可并行）

> 原则：**契约一旦写定，后端与前端同功能并行**。下面按「可立即并行」分组。

**第一批（本周可开，契约易定）**
- F1（后端 B1 落库 / 前端 注册+语言页）— 先定 auth/users 契约
- F5（后端 B2 trigger / 前端 定位+弹层）— 复用现有 nearby+guide，最快出成果
- F7（后端 B3 tts / 前端 播放器）— 语音是初赛红线，早开工

**第二批**
- F4（后端 B4 amap 步行 / 前端 地图 polyline）
- F6 加固（B5 低置信回退）
- F10 个人中心收口

**第三批（复赛）**
- F8 / F9 / B8 天气人流 / B11 多语 agent

---

## ✅ 总进度看板（功能驱动）

- [x] F1 注册登录+语言（后端 B1 落库 + JWT 完成 ✅ 2026-07-14；语言贯穿待后续）
- [x] F2 偏好输入
- [x] F3 路线推荐
- [~] F4 地图+调整（后端待 B4 步行路径）
- [ ] F5 位置触发讲解（后端待 B2）
- [x] F6 拍照识别（可加固 B5）
- [ ] F7 语音导览（后端待 B3）
- [ ] F8 多模态生成（复赛）
- [ ] F9 明信片+回忆（复赛）
- [~] F10 个人中心（待 F1 落库 + F9）

---

*— 清单版本 v1.0（feature-driven）| 2026-07-14 | 基于 report v4.5 + 代码核实 | 与 `开发计划与清单.md`（phase 版）互补 —*
