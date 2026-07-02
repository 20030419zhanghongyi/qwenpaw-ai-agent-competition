# Routes Feature Plan

> 当前可执行版路线规划计划。
> 范围限定为无 API key 的后端 routes 功能目录。

## 本轮目标

把本目录从“模板匹配 API”升级成一套可扩展的离线路线规划骨架，并保持对现有前端的兼容性。

本轮完成后，路线模块应具备：

`模板召回 -> 候选 POI 召回 -> 约束式排线 -> （预留 Agent 微调接口）`

## 本轮模块分工

### `repository.py`

- 继续作为路线模板读取与后续存储替换点

### `matcher.py`

- 作为统一入口编排器
- 负责模板召回、候选池构建、约束式排线与结果整合

### `candidate_selector.py`

- 负责无 API key 的候选 POI 召回
- 当前只依赖本地数据与可选 `weights.json`

### `route_constructor.py`

- 负责无 API key 的约束式排线
- 当前控制总时长、步行距离、少走路、少回头路
- 已支持在预算内插入候选点，以及在超约束时优先替换节点再裁剪

### `explain.py`

- 负责统一整理 explanation block
- 把命中理由、约束说明、候选点摘要从编排逻辑中拆出来

### `adjuster.py`

- 当前实现为规则版微调器
- 负责承接 `/routes/adjust` 的无模型第一版
- 下一阶段再替换为 QwenPaw Agent 版本

## 本轮先做哪些文件

P0：

- `repository.py`
- `matcher.py`
- `api.py`
- `candidate_selector.py`
- `route_constructor.py`
- `explain.py`
- `adjuster.py`

P1：

- `CHECKLIST.md`
- `README.md`
- `PLAN.md`
- 模块测试

P2：

- 预留向量召回替换点说明

## 接口兼容性

现有接口保持：

- `GET /api/v1/routes`
- `GET /api/v1/routes/{route_id}`

`POST /api/v1/routes/match` 升级为统一入口，但保持旧字段兼容：

- 保留：`route` / `score` / `reasons`
- 新增可选字段：`selected_template`、`candidate_pois`、`applied_constraints`、`explanation`

新增：

- `POST /api/v1/routes/adjust`

当前为规则版自然语言微调，占位但可用。

这样前端即使暂时不消费新字段，也不会被这轮改动阻断。

## 下一阶段如何接 Agent / 向量

### 接 Agent

未来新增 `adjuster.py`，负责：

- 接收自然语言需求
- 基于当前模板路线与候选池做结构化调整
- 输出 `added_nodes` / `removed_nodes` / `reordered_nodes` / `rationale`

当前规则版已经先把这个返回结构固定下来，方便后续无缝替换。

### 接向量

未来优先增强 `candidate_selector.py`：

- 当前规则召回继续保留
- 再加入 embedding 相似度排序
- 形成“规则 + 向量”的候选点召回

## 本轮验收

- `/routes/match` 在没有 `weights.json` 时仍能返回稳定结果
- 返回结果包含模板命中理由和约束应用说明
- `/routes/adjust` 能对“少走路 / 想拍照 / 不要回头路”返回结构化调整结果
- 候选 POI 召回可返回至少一个合理候选
- 约束式排线能在部分场景下裁剪尾部节点，避免超时或过度步行
