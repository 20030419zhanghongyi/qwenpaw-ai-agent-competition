# Routes Feature Checklist

> 按当前仓库真实状态初始化，并根据当前工作区代码、数据文件与测试结果更新。

## 已完成

- [x] 路线功能代码已集中到 `backend/app/features/routes/`
- [x] 路线相关说明文件已齐备：`README.md` / `PLAN.md` / `CHECKLIST.md`
- [x] `api.py` 已接入统一 routes 路由
- [x] `repository.py` 已作为模板读取包装层存在
- [x] `matcher.py` 已存在并承担模板召回入口
- [x] `data/routes.json` 与 `data/pois.json` 已作为 routes 功能的数据输入接入
- [x] `README.md` 已重写为无 API key 阶段说明
- [x] `PLAN.md` 已重写为当前可执行计划
- [x] `candidate_selector.py` 已实现无 API key 候选 POI 召回
- [x] `data/weights.json` 已落地，包含 `poi_heat` / `crowd_risk` / `pain_point_tags` / `alt_poi_candidates` / `theme_bias`
- [x] `route_constructor.py` 已实现无 API key 约束式排线
- [x] `explain.py` 已把解释层从编排逻辑中拆出
- [x] `adjuster.py` 已实现无 API key 规则版微调骨架
- [x] `POST /api/v1/routes/match` 已返回扩展字段：`selected_template` / `candidate_pois` / `applied_constraints` / `explanation`
- [x] `/api/v1/routes/adjust` 已提供可用的规则版占位接口
- [x] `/api/v1/routes/adjust` 已支持少走路 / 拍照点补充 / 顺路优化等高频指令骨架

## 本轮仍待补强

- [x] 候选 POI 召回已接入更丰富的权重信号，不再只依赖 `poi_heat`
- [x] 约束式排线已从“尾部裁剪”升级到“可替换节点 + 可插入节点”
- [x] `POST /api/v1/routes/adjust` 已支持基础节点增删改排
- [x] 规则版 adjust 升级为 QwenPaw Agent 版 adjust —— `/routes/adjust` 先 agent 后规则 fallback + `agents/route_agent.py` + `skills/route-adjust/SKILL.md`；已端到端验证（2026-07-12）：`route` agent + 技能就位、`ROUTE_AGENT_ENABLED=true`，实测 `source=agent`，agent 把「少走点路」→ `physical:less-walk`+`remove_tail`，排线引擎裁末端、压到 2.4km
- [ ] explanation block 继续细化成更适合前端直接渲染的展示结构
- [ ] 路线数据规模仍偏小，当前工作区仅有 6 条模板路线与约 14 个 POI，后续需继续扩充候选池

## 本轮测试与验收

- [x] 路线列表接口可用
- [x] 路线详情接口可用
- [x] `/routes/match` 在无 `weights.json` 时可用
- [x] `/routes/adjust` 已有固定场景测试覆盖
- [x] 已补固定场景测试样例
- [x] `backend/tests/test_api.py` 已覆盖 routes match / adjust / candidate pool / route constructor 关键场景
- [x] 已新增离线权重相关测试，验证 `weights.json` 结构与候选召回权重信号生效
- [x] 本地执行 `pytest -q backend/tests/test_api.py` 通过（21 passed）
- [x] README / PLAN / CHECKLIST 已可指导下一位工程师继续实现
