"""③ 护栏 guardrails（Phase 3 实现）。

职责：调用 QwenPaw 前后置 hook ——
- 前置：注入 ethics base（`ethics/prompts/_ethics_base.md`）
- 后置：跑 content-safety-review + 事实核对 + 低置信回退（`ethics/qwenpaw-skills/`）

ethics 4 技能既挂内层 agent、也作外层 hook（两处都留截图）。
Phase 3 在此目录新建模块，例如：
    hooks.py     # 前后置 hook 注册点
    fallback.py  # 低置信 / 失败回退策略
"""
