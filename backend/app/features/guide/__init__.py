"""拍照识别 / 文化讲解 feature（Phase 4）。

竖切只落 ``POST /api/v1/guide/photo``（上传图 → 脱敏 → Qwen-VL 描述）；
讲解（RAG + guide agent）与 ``/guide/generate`` 留下一增量。
"""
