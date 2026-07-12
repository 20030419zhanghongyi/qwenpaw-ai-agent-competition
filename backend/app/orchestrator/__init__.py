"""① 编排路由 orchestrator（Phase 3 实现）。

职责：用户意图 → 分发给哪个 agent（需求理解 / 路线微调 / 文化讲解），
可经 QwenPaw `agents chat --from … --to …` 让多 agent 协作。

Phase 3 在此目录新建模块，例如：
    router.py   # 意图分类 → 路由
    collaborate.py  # 多 agent 对话编排
统一封装为对 services / api 层的调用入口。
"""
