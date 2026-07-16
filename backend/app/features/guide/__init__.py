"""拍照识别、位置触发与文化讲解 feature。

- ``POST /api/v1/guide/trigger``：PostGIS 附近 POI 探测 + 会话级提示去重；
  用户确认后再调用 ``/guide/generate``。
- ``POST /api/v1/guide/photo``：上传图 → 脱敏 → Qwen-VL 描述。
- ``POST /api/v1/guide/generate``：RAG 取料 → guide agent 生成讲解。
"""
