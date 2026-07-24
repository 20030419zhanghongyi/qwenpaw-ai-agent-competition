# Frontend — Macau StoryWalk Web MVP

React + Vite + TypeScript 前端。比赛主线已接到可演示闭环：

`语言选择 → 登录/偏好 → 路线结果（高德地图 + 微调）→ 位置/拍照讲解 + TTS → 打卡 → 明信片 / 个人中心`

路线策略与总计划一致：

- **预设路线模板** 冷启动与兜底
- **POI 标签 / 规则约束** 时长、步行、区域连续性
- **QwenPaw Agent** 自然语言理解、路线微调、讲解与识图（经后端转发）

## 当前定位（与代码对齐）

已不是「仅三页 + 插画占位」阶段。`src/App.tsx` 路由包括：

| 路径 | 页面 | 能力 |
|------|------|------|
| `/` | `LanguagePage` | 四语选择 |
| `/auth` | `AuthPage` | 注册 / 登录（JWT） |
| `/preferences` | `PreferencePage` | 结构化偏好 + 自然语言（intent）+ 偏好引导聊天 |
| `/walk` | `RouteResultPage` | `routes/match`、高德 `MapRouteView` + `walk-path`、NL `adjust`、GPS `guide/trigger`、行程打卡 |
| `/guide` | `GuidePage` | `guide/generate`、追问、拍照识别、TTS 播放 |
| `/postcards*` | 明信片创建 / 画廊 / 详情 | 打卡后生成明信片 |
| `/profile` | `ProfilePage` | 个人中心入口 |

主要 API 封装：`src/api/client.ts`、`routes.ts`、`trips.ts`、`postcards.ts`、`auth.ts`、`guide-trigger.ts`。

**依赖后端 / 密钥时才完整可用的部分**（代码已接，环境未配会失败或降级）：

- `VITE_AMAP_API_KEY` / `VITE_AMAP_SECURITY_CODE`（地图 JS API）
- 后端高德 Web 服务 Key、DashScope TTS/OSS、QwenPaw Agent 开关

**未做 / 非当前交付**（勿在 README 里写成已完成）：

- 微信小程序客户端（仍是 Web MVP）
- 实时人流/天气前端展示（后端以离线权重为主；需进一步确认部署侧是否接了 live API）

## 启动

```bash
cd frontend
npm install
npm run dev
```

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`（`vite.config.ts` 将 `/api` 代理到后端）
- 仓库根 `.env` 的 `VITE_*` 由 `envDir: ".."` 读取

```bash
VITE_API_BASE_URL=          # 留空走代理；生产填后端域名
VITE_AMAP_API_KEY=
VITE_AMAP_SECURITY_CODE=
```

## 目录结构

```text
frontend/
├── README.md
├── FRONTEND_PLAN.md          # 历史执行计划，可能滞后于本 README
├── design/
├── src/
│   ├── App.tsx
│   ├── api/                  # client / routes / trips / postcards / auth / guide-trigger
│   ├── pages/                # Language / Auth / Preference / RouteResult / Guide / Postcard* / Profile
│   ├── components/
│   │   ├── map/MapRouteView.tsx
│   │   ├── guide/            # 讲解分段、拍照面板
│   │   ├── route/            # 节点列表、理由 chips
│   │   ├── route-adjust/     # 路线微调面板
│   │   ├── preference/       # 偏好聊天
│   │   ├── postcard/
│   │   └── layout/
│   ├── state/                # Auth / Walk / Trip contexts
│   ├── types/
│   ├── lib/
│   └── i18n.ts
└── vite.config.ts
```

## 模块要点

### 路线结果页 `RouteResultPage`

- 调 `matchRoutes` / `adjustRoute` / `fetchWalkPath`
- `navigator.geolocation.watchPosition` → `triggerGuide`；确认后再 `generateGuide`
- 行程 `createTrip` / `checkIn`

### 讲解页 `GuidePage`

- POI 讲解、追问、`recognizeGuidePhoto`、`synthesizeTts` 音频 URL 播放

### 状态

- `WalkContext`：语言、偏好、当前匹配路线会话
- `AuthContext` / `TripContext`：登录与行程打卡

## 设计与交互原则（比赛）

1. **先解释再炫技**：推荐理由、来源/置信度、调整前后变化要看得见。
2. **行程可执行**：时长、步行、节点顺序、调整入口优先于大段 AI 正文。
3. **Agent 结果可回退**：自然语言微调失败时后端可降级规则版；UI 应展示 `source` 与说明。
4. **移动端优先**：为后续小程序迁移保留窄屏布局习惯。

## 对应文档

- 根 README（当前阶段总览）：[`../README.md`](../README.md)
- 系统架构：[`../docs/system-architecture.md`](../docs/system-architecture.md)
- 功能清单（可能滞后）：[`../plan/功能开发清单-feature-driven.md`](../plan/功能开发清单-feature-driven.md)
- 前端历史计划：[`FRONTEND_PLAN.md`](./FRONTEND_PLAN.md)
