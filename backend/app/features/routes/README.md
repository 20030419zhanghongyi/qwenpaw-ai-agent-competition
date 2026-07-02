# Routes Feature

本目录集中放置「路线规划」相关的后端代码。

## 1. 预设路线数据在哪里？

预设路线模板当前放在：

- [data/routes.json](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/data/routes.json:1)

相关 POI 数据放在：

- [data/pois.json](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/data/pois.json:1)

它们继续留在 `data/`，因为它们属于全局种子数据，不是 routes 功能目录内部私有代码。

## 2. 路线功能代码在哪里？

路线功能代码统一放在：

- [backend/app/features/routes](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/backend/app/features/routes)

这个目录负责“路线能力”，不是原始数据存放处。

## 3. 本目录当前负责什么 / 不负责什么？

### 当前负责

- 读取预设路线模板
- 模板路线初筛
- 无 API key 的候选 POI 召回
- 无 API key 的约束式排线
- 路线相关 API
- 路线功能文档、计划、checklist

### 当前不负责

- QwenPaw Agent 自然语言微调
- embedding / pgvector 向量召回
- 前端地图渲染
- 讲解文本生成
- TTS / 语音播放

## 4. 无 API key 阶段现在做到哪一步？

当前已落地的是一条保守但可扩展的离线路线规划链路：

`模板召回 -> 候选 POI 召回 -> 约束式排线 -> （预留 Agent 微调接口）`

说明：

1. 先从 `data/routes.json` 中召回合适的模板路线
2. 再围绕模板节点召回同主题 / 同标签 / 同区的候选 POI
3. 再按时长、步行距离、少走路、少回头路做规则化排线
4. 本轮不接 API key，不做自然语言改路线

## 当前目录结构

```text
backend/app/features/routes/
├── __init__.py
├── api.py
├── repository.py
├── matcher.py
├── candidate_selector.py
├── route_constructor.py
├── explain.py
├── adjuster.py
├── README.md
├── PLAN.md
└── CHECKLIST.md
```

## 文件职责

### `repository.py`

路线模板读取包装层。

当前仍然透传 `app.db.data`，但后续切 Postgres / pgvector / hybrid store 时，优先从这里替换。

### `matcher.py`

路线统一入口编排器。

当前负责：

- 模板初筛
- 叠加基础理由
- 构建候选 POI 池
- 调用约束式排线
- 输出兼容前端的 match 结果

### `candidate_selector.py`

无 API key 的候选点召回层。

当前依赖：

- `theme`
- `suitable_for`
- `district`
- `replaceable_with`
- `weights.json` 的 `poi_heat`（若存在）

### `route_constructor.py`

无 API key 的约束式排线层。

当前控制：

- 总时长
- 步行距离
- 少走路
- 少回头路
- 候选节点插入
- 候选节点替换

当前实现是保守规则版，不做全局最优求解，但已经不再只会“裁尾部节点”，而是会按约束优先尝试：

1. 在预算内按兴趣插入候选点
2. 超约束时优先把末端节点替换成更紧凑的候选点
3. 最后才裁剪末端节点

### `explain.py`

路线解释层。

负责把：

- 模板命中理由
- 约束应用说明
- 候选点概览

统一整理成前端更容易消费的 explanation block。

### `adjuster.py`

无 API key 的规则版路线微调器。

当前不是 QwenPaw Agent，但已经提供未来 Agent 版本会沿用的结构化输出骨架：

- `selected_template`
- `preference_before`
- `preference_after`
- `candidate_pois`
- `removed_nodes`
- `added_nodes`
- `reordered_nodes`
- `rationale`
- `applied_constraints`
- `explanation`

### `api.py`

当前开放：

- `GET /api/v1/routes`
- `POST /api/v1/routes/match`
- `GET /api/v1/routes/{route_id}`

其中 `POST /match` 已升级为：

- 模板召回
- 候选 POI 召回
- 约束式排线

并返回兼容扩展字段：

- `route`
- `score`
- `reasons`
- `selected_template`
- `candidate_pois`
- `applied_constraints`
- `explanation`

另外本目录现在新增：

- `POST /api/v1/routes/adjust`

它是**无 API key 的规则版 adjust 接口**，先支持少量高频自然语言偏好，后续可平滑替换成 Agent 版本。

## 设计原则

路线规划不走两个极端：

- 不走“纯模板死匹配”
- 不走“纯大模型自由生成”

当前采用的目标架构是：

`预设路线模板 + POI 候选召回 + 规则约束 + Agent 微调`

在无 API key 阶段，我们先把前 3 步做稳。

## 未来怎么接 Agent / 向量？

下一阶段建议补：

- `adjuster.py`：从规则版升级为 QwenPaw 路线微调
- embedding / pgvector：替换或增强 `candidate_selector.py` 的相似点召回
- `explain.py`：统一输出更适合前端展示的解释块

## 关联文件

- 路线种子数据：[data/routes.json](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/data/routes.json:1)
- POI 种子数据：[data/pois.json](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/data/pois.json:1)
- 路线模型：[backend/app/models/route.py](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/backend/app/models/route.py:1)
- 路线计划：[backend/app/features/routes/PLAN.md](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/backend/app/features/routes/PLAN.md:1)
- 路线 checklist：[backend/app/features/routes/CHECKLIST.md](/Users/gracexiao/Documents/GitHub/qwenpaw-ai-agent-competition/backend/app/features/routes/CHECKLIST.md:1)
