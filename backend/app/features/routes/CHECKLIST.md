# Routes Feature Checklist

> 按当前仓库真实状态初始化，并根据本轮完成情况更新。

## 已完成

- [x] 路线功能代码已集中到 `backend/app/features/routes/`
- [x] `api.py` 已接入统一 routes 路由
- [x] `repository.py` 已作为模板读取包装层存在
- [x] `matcher.py` 已存在并承担模板召回入口
- [x] `README.md` 已重写为无 API key 阶段说明
- [x] `PLAN.md` 已重写为当前可执行计划
- [x] `candidate_selector.py` 已实现无 API key 候选 POI 召回
- [x] `route_constructor.py` 已实现无 API key 约束式排线
- [x] `explain.py` 已把解释层从编排逻辑中拆出
- [x] `adjuster.py` 已实现无 API key 规则版微调骨架
- [x] `/api/v1/routes/adjust` 已提供可用的规则版占位接口

## 本轮仍待补强

- [ ] 候选 POI 召回进一步接入更丰富的权重信号（当前仅使用可选 `poi_heat`）
- [x] 约束式排线已从“尾部裁剪”升级到“可替换节点 + 可插入节点”
- [x] `POST /api/v1/routes/adjust` 已支持基础节点增删改排
- [ ] 规则版 adjust 升级为 QwenPaw Agent 版 adjust
- [ ] explanation block 继续细化成更适合前端直接渲染的展示结构

## 本轮测试与验收

- [x] 路线列表接口可用
- [x] 路线详情接口可用
- [x] `/routes/match` 在无 `weights.json` 时可用
- [x] `/routes/adjust` 已有固定场景测试覆盖
- [x] 已补固定场景测试样例
- [x] README / PLAN / CHECKLIST 已可指导下一位工程师继续实现
