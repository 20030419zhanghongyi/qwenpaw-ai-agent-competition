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
| `/stories/:storyId` | `StoryCoverPage` | Story Walk 封面、登录回跳与会话开始 |
| `/story-sessions/:sessionId/map` | `StoryMapPage` | 六站故事地图、进度、花瓣与当前任务 |
| `/story-sessions/:sessionId/nodes/:nodeId` | `StoryScenePage` | 到达确认、剧情、知识卡、谜题、提示与奖励 |
| `/story-sessions/:sessionId/ending` | `StoryEndingPage` | 结局选择、今日补记与完成回顾 |

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
- Compose 后端：`http://localhost:8001`（`vite.config.ts` 默认将 `/api` 代理到该端口；本机 Uvicorn 可通过 `VITE_BACKEND_PROXY_TARGET` 覆盖）
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
- `StoryContext`：Story Walk 会话恢复、动作串行化、章节快照与错误状态

### Story Walk V4

当前首个故事为《莲城双图：未尽之图》，入口为：

```text
http://localhost:5173/stories/lotus_city_double_map
```

- 前端以 `/api/v1/stories` 和 `/api/v1/story-sessions` 的实际响应为准，
  不在浏览器内保存答案或判题规则。
- 故事图片统一通过 `src/features/story/assets/storyAssetManifest.ts`
  映射到 `public/story/v4/` 的分目录素材。图片缺失或加载失败时会自动
  回退到纸张纹理占位图，不会阻塞流程。
- 故事问答抽屉复用现有 `/guide/ask` 能力；服务不可用时不影响主线。
- 跳过谜题必须二次确认，且服务端仍记录跳过结果。

检查 05 文档、资产 manifest 和正式素材是否存在编号、文件名、比例或
遗漏冲突：

```powershell
cd frontend
npm run check:story-assets
```

#### 开发与生产显示

资产调试信息使用 Vite 内置的 `import.meta.env.DEV` 判断，不需要修改
`.env`：

```powershell
# 开发环境：缺图占位会显示资产编号和具体素材说明
cd frontend
npm run dev

# 生产环境：先构建，再预览 dist；缺图时只显示简洁说明
cd frontend
npm run build
npm run preview
```

部署平台也应发布 `npm run build` 生成的 `dist/`，此时
`import.meta.env.PROD` 为 `true`、`import.meta.env.DEV` 为 `false`。
正式图片成功加载时两种环境都不会额外覆盖资产编号；编号只用于开发
环境中的缺图、未登记素材和花瓣组合调试信息。

#### Story Walk 浏览器冒烟测试

先启动 Compose 后端与 Vite 前端，再从仓库根目录运行：

```powershell
$env:STORY_TEST_EMAIL = "your-test-account@example.com"
$env:STORY_TEST_PASSWORD = "your-test-password"
$env:STORY_SCREENSHOT_DIR = Join-Path $env:TEMP "story-v4-screenshots"
node .\scripts\story-v4-browser-smoke.mjs
```

脚本仅使用 Node.js 内置模块，会自动寻找 Chrome、Edge 或 Chromium。
测试使用真实后端会话，覆盖偏好页故事邀请、登录回跳、序章 Agent、
占位图放大、单气泡与历史对话、立绘位置、漫画正反向翻页、六站推进、
证据链图片查看与触控重排、窗框拼合的点按和触控拖放、地图图层边界、
跳关确认、第五瓣合成及减少动态效果降级、结局补记、刷新恢复，并检查
360、390、430 像素移动端视口。浏览器 profile 创建在操作系统临时目录，
不使用 `frontend/.tmp/`。

可选变量：

```powershell
$env:STORY_BASE_URL = "http://localhost:5173"
$env:STORY_BROWSER_PATH = "C:\path\to\browser.exe"
$env:STORY_TIMEOUT_MS = "30000"
# 偏好 Agent 暂不可用时，只跳过偏好页邀请测试，其余故事测试照常运行
$env:STORY_SKIP_PREFERENCE_ENTRY = "1"
```

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
