"""② 评测调优 eval（Phase 2 实现，核心）。

职责：读 `harness/datasets/` 测试集 → 跑路线/讲解 agent → 按 `harness/rubrics/`
打分（规则项为主 + LLM-judge 为辅）→ 落 `harness/results/`，并支持调优循环
（看哪类分低 → 改 SKILL.md / 补知识 → 重跑 → before/after 对比）。

Phase 2 在此目录新建模块，例如：
    runner.py    # 跑批
    scoring.py   # 规则项 + LLM-judge 打分
    report.py    # 出分数表 / 曲线图
"""
