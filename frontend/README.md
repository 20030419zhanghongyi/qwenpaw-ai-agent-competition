# Frontend — Macau StoryWalk Web MVP

React + Vite + TypeScript 前端。当前目标不是一次做成完整旅游产品，而是围绕比赛主线先跑通：

`语言选择 -> 偏好输入 -> 路线结果 -> 节点讲解 -> 后续可接地图 / Agent / 位置提醒`

这套前端会持续对齐总计划中的混合路线策略：

- **预设路线模板** 负责冷启动与兜底
- **POI 标签 / 向量召回** 负责补充候选点
- **规则约束** 负责时长、步行、区域连续性
- **QwenPaw Agent 微调** 负责自然语言理解、换点、解释与讲解生成

## 当前定位

当前代码处于 **Phase 2 Web MVP**：

- 三页流程：语言选择 → 偏好输入 → 路线结果（插画地图占位）
- 已接：`POST /api/v1/routes/match`、`GET /api/v1/pois`
- 结果页展示路线说明、推荐理由、节点列表（POI 名称由列表接口补全）
- 视觉来自 Lovable 设计包（Morandi 纸色 + sage）

尚未完成：

- 真地图与步行 polyline
- 路线轻度调整 UI / `routes/adjust`
- 位置触发讲解、语音、拍照识别

## 启动

```bash
cd frontend
npm install
npm run dev
```

默认开发地址：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

本地开发时 `/api` 由 `vite.config.ts` 代理到后端。

## 环境变量

前端当前只依赖一个变量：

```bash
VITE_API_BASE_URL=
```

说明：

- 留空：走 Vite 代理，开发最方便
- 生产：填写后端域名，如 `https://api.example.com`

## 当前目录

```text
frontend/
├── README.md
├── FRONTEND_PLAN.md
├── design/
├── index.html
├── package.json
├── vite.config.ts
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── api/client.ts
    ├── types/
    ├── lib/preference.ts
    ├── state/WalkContext.tsx
    ├── pages/
    │   ├── LanguagePage.tsx
    │   ├── PreferencePage.tsx
    │   └── RouteResultPage.tsx
    ├── components/
    │   ├── brand/
    │   ├── common/
    │   └── route/
    └── assets/
```

流程：`/` 语言 → `/preferences` 偏好并调用 `POST /api/v1/routes/match` → `/walk` 展示匹配结果（插画地图占位 + 节点列表 + 推荐理由）。

## 现有模块说明

### `src/App.tsx`

当前主流程页，负责：

- 三步状态切换：`lang -> pref -> result`
- 组织偏好数据
- 并发请求路线匹配和 POI 列表
- 展示 top route 与节点讲解摘要

后续建议把这里拆成：

- `pages/LanguagePage`
- `pages/PreferencePage`
- `pages/RouteResultPage`
- `components/RouteCard`
- `components/RouteNodeList`
- `components/ReasonChips`

### `src/api/client.ts`

当前承担两类职责：

- 定义前端使用的 API 类型
- 封装 fetch 请求

后续建议扩展为：

- `matchRoutes()`
- `previewRoute()`
- `adjustRoute()`
- `generateGuide()`
- `triggerGuide()`
- `uploadGuidePhoto()`

并考虑把类型拆分到 `src/types/`。

### `src/i18n.ts`

当前是极简多语言字典。比赛阶段足够轻，但后续页面变多后建议：

- 将文案按页面拆分
- 给路线标签、体力标签、原因标签建立统一映射
- 确保与后端词表一致，避免 `lessWalk` / `less-walk` 这种前后端二次转换到处散落

### `src/index.css`

当前是 MVP 基础样式。后续继续演进时，建议优先做：

- 设计 token 化：颜色、间距、圆角、阴影、字号
- 明确移动端断点
- 为地图页、卡片页、讲解页准备统一容器样式

## 与总计划对齐的前端目标

### Phase 2：Web MVP

前端的核心目标是把“可点”做出来，而不是先把“智能”做满。

必须完成：

- 语言选择
- 偏好输入
- 路线结果页
- 节点说明展示
- 基础推荐理由展示

最好一起完成：

- 地图占位区域
- 路线解释区
- 路线轻调入口

### Phase 3：QwenPaw Agent 接入

前端需要支持两类新增交互：

- 用户用自然语言补充要求
  - 例：`不想太累`
  - 例：`帮我加一个拍照点`
  - 例：`从新马路附近开始`
- 系统返回“调整前 / 调整后”的可视化对比

这一阶段前端重点不是建复杂编辑器，而是把 Agent 调整结果展示清楚：

- 选中了哪个模板路线
- 删掉了哪些点
- 换成了哪些相似点
- 为什么这么换

### Phase 4：行走中导览

前端重点变成“低打扰、强确认”：

- 用户进入 POI 缓冲区后弹提醒
- 用户确认后才播讲解
- 语音播放、暂停、重播要简单稳定
- 上传照片入口要清晰，但不是首页主入口

## 推荐页面结构

建议按下面的结构逐步演进：

```text
src/
├── api/
│   └── client.ts
├── components/
│   ├── layout/
│   ├── route/
│   ├── guide/
│   └── common/
├── pages/
│   ├── LanguagePage.tsx
│   ├── PreferencePage.tsx
│   ├── RouteResultPage.tsx
│   ├── GuidePage.tsx
│   └── ProfilePage.tsx
├── state/
│   ├── preference.ts
│   ├── route.ts
│   └── guide.ts
├── types/
├── utils/
├── i18n/
└── main.tsx
```

当前不必一次性重构，但新增功能时尽量往这个方向靠，避免 `App.tsx` 继续变成大文件。

## 前端数据模型建议

为了匹配新的路线策略，前端后续要准备接这些字段：

### POI 扩展字段

- `visit_duration_min`
- `best_time`
- `indoor_outdoor`
- `crowd_level_base`
- `photo_score`
- `food_score`
- `history_score`
- `family_score`
- `night_score`
- `walkability_score`
- `region_cluster`
- `nearby_poi_ids`

这些字段的用途：

- 展示“为什么推荐这个点”
- 做路线调整时的筛选 chips
- 做相似点替换说明

### 路线调整结果字段

建议后端未来返回：

- `selected_template`
- `candidate_pois`
- `removed_nodes`
- `added_nodes`
- `reordered_nodes`
- `rationale`

前端可以据此做“调整前后对比卡片”。

## 设计与交互原则

### 1. 先解释，再炫技

比赛里最容易失分的不是功能少，而是“为什么推荐这条路线”说不清。前端必须优先把这些讲清楚：

- 命中了哪些兴趣
- 为什么步行强度适合
- 为什么替换成这个点
- 内容来源是什么

### 2. 路线结果页要像“可执行行程”，不是一段 AI 输出

用户第一眼应该看到：

- 总时长
- 步行距离
- 节点顺序
- 每站建议停留
- 可调整入口

而不是先看到大段说明文字。

### 3. 所有 Agent 结果都要可视化、可回退

比如用户说“加个拍照点”，前端不应只替换一坨数据，而要让用户知道：

- 加了哪个点
- 删了哪个点
- 总时长增加了多少

### 4. 移动端体验优先

虽然现在是 Web MVP，但未来要迁移小程序，所以从现在开始就应避免：

- 只适合桌面的宽布局
- 过多 hover 交互
- 依赖复杂表单输入

## 开发建议

### API 协作

- 所有前后端标签词表统一维护
- 新接口先约定响应 shape，再写 UI
- Agent 返回数据必须结构化，前端不要解析自然语言正文来驱动 UI

### 状态管理

当前用 React 本地 state 足够。

当这些状态出现后，可考虑引入轻量状态层：

- 当前用户偏好
- 当前路线结果
- 当前选中 POI
- 当前讲解播放状态

在比赛阶段不建议为了“架构完整”过早上重状态库。

### 测试重点

前端最值得先测的是：

- 偏好到请求 payload 的映射是否正确
- route result 是否能稳定渲染缺失字段
- 多语言切换是否遗漏关键按钮
- Agent 调整前后对比是否清楚

## 对应文档

- 总开发计划：[plan/开发计划与清单.md](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/plan/开发计划与清单.md:1)
- 系统架构：[docs/system-architecture.md](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/docs/system-architecture.md:1)
- 前端执行计划：[frontend/FRONTEND_PLAN.md](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/frontend/FRONTEND_PLAN.md:1)
