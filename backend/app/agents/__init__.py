"""QwenPaw Agent 层（Phase 3 实现）。

设计书定义 6 个 Agent，分两批落地：
  Phase 3（核心 3 个）：
    - 用户需求理解 Agent
    - 路线配对与微调 Agent
    - 文化讲解 Agent
  Phase 4+（扩展 3 个）：
    - 图像识别讲解 Agent
    - 多语言生成 Agent
    - 反馈优化 Agent

Phase 1/2 此目录仅占位。Phase 3 在此目录下新建模块，例如：
    intent_agent.py / route_agent.py / guide_agent.py
统一封装为：
    def invoke(messages, tools, **kwargs) -> dict
并在 services 层调用，避免路由层直接依赖 QwenPaw SDK。
"""
