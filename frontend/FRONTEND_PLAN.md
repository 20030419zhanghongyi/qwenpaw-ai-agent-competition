# Frontend Plan — Macau StoryWalk

> 基于仓库总计划拆出的前端执行版。
> 目标是让前端同学能按页面、组件、接口和阶段直接推进，而不是只看总计划里的抽象描述。

---

## 1. 前端目标

前端在比赛阶段承担三层任务：

1. 把核心闭环做成**可点、可懂、可演示**
2. 把路线推荐结果做成**可解释、可调整**
3. 在 Phase 4 把系统从“出发前工具”推进到“行走中导览伙伴”

前端不是纯展示层，而是体验成败的主战场。路线推荐再聪明，如果页面无法解释推荐逻辑、无法体现调整前后差异，Demo 观感也会大打折扣。

---

## 2. 当前状态

### 已有

- 三页流程：语言选择、偏好输入、结果展示（Lovable UI 移植）
- API：`POST /api/v1/routes/match`、`GET /api/v1/pois`
- Morandi 设计 token + 插画地图占位
- 推荐理由、节点列表、触发弹窗 UI 壳

### 缺少

- 真地图与步行 polyline
- 路线解释增强 / Agent 调整结果展示
- 位置提醒、语音播放、拍照上传

---

## 3. 前端架构原则

- 以**移动端优先**设计页面和组件
- 以**结构化数据展示**为主，不依赖前端解析大段模型文案
- 优先展示“为什么推荐”，再展示“AI 多聪明”
- 所有路线调整都要能看出变化，不做黑箱替换
- 尽量保持前端模块轻量，避免比赛期过度工程化

---

## 4. 阶段拆解

### Phase 2：Web MVP（当前优先级最高）

#### 目标

把以下流程稳定跑通：

`选择语言 -> 选择偏好 -> 请求路线 -> 展示路线与节点 -> 查看讲解摘要`

#### 页面任务

- [ ] `LanguagePage`：语言选择入口
- [ ] `PreferencePage`：偏好选择页
- [ ] `RouteResultPage`：路线结果页
- [ ] `PoiGuideCard`：节点讲解摘要卡片

#### 组件任务

- [ ] `ChipSelector`：兴趣、体力、出行类型选择
- [ ] `RouteSummaryCard`：总时长、步行、体力、说明
- [ ] `ReasonChips`：推荐理由
- [ ] `RouteNodeList`：节点列表
- [ ] `EmptyState` / `ErrorState` / `LoadingState`

#### 接口任务

- [ ] 接好 `POST /api/v1/routes/match`
- [ ] 接好 `GET /api/v1/pois`
- [ ] 为后续 `GET /api/v1/routes/{id}` 预留类型

#### 体验要求

- [ ] 首屏 5 秒内能让评委理解“这是做什么的”
- [ ] 路线结果必须一屏内看到关键信息
- [ ] 推荐理由必须清楚可读
- [ ] 多语言切换不影响核心流程

### Phase 3：Agent 路线微调

#### 目标

支持用户通过自然语言对路线做轻调，并清楚展示调整结果。

#### 页面 / 组件任务

- [ ] `AdjustmentPanel`：自然语言输入框
- [ ] `AdjustmentDiffCard`：调整前后对比
- [ ] `CandidatePoiList`：相似点 / 替换点候选
- [ ] `RationaleBlock`：AI 调整原因

#### 接口任务

- [ ] 接 `POST /api/v1/routes/adjust`
- [ ] 支持展示 `selected_template`
- [ ] 支持展示 `added_nodes` / `removed_nodes` / `reordered_nodes`
- [ ] 支持展示 `candidate_pois`

#### 体验要求

- [ ] 用户能看懂“加了什么、删了什么”
- [ ] 用户能看懂“为什么这么改”
- [ ] 总时长、步行距离变化必须同步更新

### Phase 4：位置提醒 / 语音 / 拍照

#### 目标

支持行走中导览的关键体验闭环。

#### 页面 / 组件任务

- [ ] `MapRouteView`：地图与节点 marker
- [ ] `TriggerToast`：接近 POI 时提醒
- [ ] `AudioPlayer`：语音播放控件
- [ ] `PhotoUploadPanel`：拍照识别上传入口
- [ ] `GuideModal`：触发后展示讲解

#### 接口任务

- [ ] 接 `POST /api/v1/guide/trigger`（后端已就绪：确认提示 + 防重复）
- [ ] 接 `POST /api/v1/guide/generate`（后端已就绪）
- [ ] 接 `POST /api/v1/guide/photo`（后端已就绪：含低置信重拍/手选状态）
- [ ] 接 TTS 返回的音频 URL

#### 体验要求

- [ ] 位置提醒必须先确认后播报
- [ ] 播放控件足够简单，别做复杂播放器
- [ ] 上传识别失败时要有友好兜底

### Phase 5：小程序迁移准备

#### 目标

提前为 Taro / 小程序复用做准备。

#### 技术任务

- [ ] 避免把业务逻辑写死在 `App.tsx`
- [ ] API 层与 UI 层解耦
- [ ] i18n 文案拆分
- [ ] 控件设计尽量移动端友好

---

## 5. 页面结构建议

```text
src/
├── api/
│   └── client.ts
├── components/
│   ├── common/
│   ├── route/
│   ├── guide/
│   └── map/
├── pages/
│   ├── LanguagePage.tsx
│   ├── PreferencePage.tsx
│   ├── RouteResultPage.tsx
│   ├── GuidePage.tsx
│   └── ProfilePage.tsx
├── types/
├── utils/
├── i18n/
├── state/
└── main.tsx
```

说明：

- 比赛期不强制一次性完成重构
- 新功能尽量按这个结构新增
- 避免继续把所有逻辑都压进 `App.tsx`

---

## 6. API 与类型演进计划

### 当前已有类型

- `POI`
- `Route`
- `RouteNode`
- `MatchResult`
- `Preference`

### 建议新增类型

- `RouteAdjustmentRequest`
- `RouteAdjustmentResult`
- `GuideGenerateRequest`
- `GuideGenerateResult`
- `GuideTriggerResult`
- `PoiCandidate`

### POI 扩展字段预留

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

用途：

- 解释推荐理由
- 展示替换原因
- 展示适配场景
- 支撑筛选 chips

---

## 7. UI 优先级

### P0

- 语言选择
- 偏好输入
- 路线结果页
- 推荐理由
- 节点卡片

### P1

- 地图视图
- 路线调整入口
- 调整前后 diff
- 候选点说明

### P2

- 位置触发
- 语音播放
- 拍照识别
- 明信片入口

---

## 8. 交互细节要求

### 偏好输入

- 以选择题、勾选为主
- 不要让用户一上来写长文本
- 自然语言微调应放在路线结果页，而不是首屏

### 路线结果

第一屏必须优先展示：

- 路线名
- 时长
- 步行距离
- 体力强度
- 推荐理由

第二屏再展示：

- 节点顺序
- 每站停留
- 节点讲解

### Agent 调整

必须清楚展示：

- 调整前模板路线
- 调整后路线
- 替换节点
- 理由说明

### 讲解展示

必须清楚展示：

- 地点名
- 讲解正文
- 观察建议
- 内容来源标签

---

## 9. 风险与防守策略

### 风险 1：前端过早复杂化

防守：

- 先把 Phase 2 页面拆清楚
- 不在比赛前期过度引入状态库和 UI 框架

### 风险 2：Agent 结果无法稳定渲染

防守：

- 强依赖结构化 schema
- 前端永远有兜底展示

### 风险 3：页面解释力不足

防守：

- 推荐理由必须是显眼区域
- 路线调整 diff 必须可视化

### 风险 4：移动端体验差

防守：

- 组件宽度、按钮密度、输入方式都按手机优先考虑

---

## 10. 本周建议任务

如果按当前状态继续推进，前端本周最值得先做的是：

- [ ] 把 `App.tsx` 拆成页面 + 基础组件
- [ ] 优化路线结果页的信息层级
- [ ] 给 `client.ts` 补充未来接口类型骨架
- [ ] 统一前后端标签映射，避免字符串分裂
- [ ] 为地图区域留出稳定布局占位

---

## 11. 验收标准

### Phase 2 验收

- 评委能在 1 分钟内理解产品主线
- 用户能在 5 分钟内独立完成一次偏好到路线的流程
- 用户能看懂为什么推荐这条路线

### Phase 3 验收

- 用户提出自然语言要求后，能看到明确调整结果
- 用户能看懂为什么换点、为什么删点

### Phase 4 验收

- 用户走近某个点时，能收到低打扰提醒
- 用户确认后能顺畅播放讲解

---

## 12. 关联文档

- 总计划：[plan/开发计划与清单.md](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/plan/开发计划与清单.md:1)
- 系统架构：[docs/system-architecture.md](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/docs/system-architecture.md:57)
- 前端说明：[frontend/README.md](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/frontend/README.md:1)
