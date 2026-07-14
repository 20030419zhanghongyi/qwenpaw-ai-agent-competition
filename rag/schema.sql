-- RAG 语义检索表 poi_chunks 的 DDL（仓库原本缺失，从 rag/ingest.py 与 rag/retrieve.py 反推）。
-- 与 backend 表共用同一个 qwenpaw 库；rag/ingest.py 只 TRUNCATE+INSERT，不建表/不建扩展。
-- embedding 维度 1024 = DashScope text-embedding-v3 默认（见 rag/ingest.py EMBED_DIM）。
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS poi_chunks (
    poi_id      text PRIMARY KEY,
    name        text,
    text        text,
    source_type text,
    embedding   vector(1024)
);

-- 余弦相似 ANN 索引（retrieve 用 <=> 算子）。用 HNSW：增量建、召回稳；
-- 不像 ivfflat 要在「建索引时」就有足够样本算质心（空表先建 ivfflat 再灌数会低召回）。
CREATE INDEX IF NOT EXISTS poi_chunks_embedding_idx
    ON poi_chunks USING hnsw (embedding vector_cosine_ops);
