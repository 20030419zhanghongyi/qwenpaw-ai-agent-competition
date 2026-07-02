# RAG — 澳门旧区知识库检索

把 POI 文化资料、街区故事、典型游客困惑表述向量化检索，供 QwenPaw 讲解 Agent 引用。

## 文件

| 文件 | 职责 | 阶段 |
|------|------|------|
| `ingest.py` | 分块 + embedding + 入 pgvector | Phase 3 实现（Phase 1 占位） |
| `retrieve.py` | `retrieve(query, k)` 检索接口 | Phase 1 关键词粗检索；Phase 3 换向量检索 |

## 数据源

- `data/pois.json` —— 结构化 POI 讲解（来源分级 `source_type`）
- `data/weights.json` —— `scripts/clean_xhs.py` 产出的离线调研权重
- 社交媒体**仅用现有离线数据集**，不做实时爬取

## Phase 3 目标

1. `ingest.py` 接 DashScope `text-embedding-v3`，写入 pgvector
2. `retrieve.py` 改向量检索（top-k，附 `source_type`）
3. backend 文化讲解 / 图像识别讲解 Agent 调 `retrieve()`，生成内容标注来源

## 试跑（Phase 1）

```bash
python rag/retrieve.py "疯堂斜巷 葡式碎石"
python rag/ingest.py        # 目前只解析、不入库
```
