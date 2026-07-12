# datasets/ —— 评测测试用例

存放「智能体调优」用的澳门文旅 query 测试集（plan P2）。

- 来源：小红书 100 笔记 / 751 评论中挑选 15–20 条，覆盖**讲解类**与**路线类**
- 每条用例：`id` / `category`(guide|route) / `input`(自然语言) / `route_id`(路线类) / `preference` / `expect`(粗粒度期望，供规则项核对)
- 由 `backend/app/eval/` 跑批时读取

> 当前为空。P2 填充 `cases.json` 后即可被评测脚本消费。
