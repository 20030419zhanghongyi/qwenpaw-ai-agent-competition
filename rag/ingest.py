"""RAG 入库：把 ``data/pois.json`` 每个 POI 向量化（DashScope text-embedding-v3，1024 维）写入 pgvector。

**POI 级 chunk**：每个 POI 一行（intro/history/architecture/story/observation_tips 拼接），
retrieve 返回整 POI —— 对齐 guide agent 需要「整份结构化资料」而非碎片字段。
embedding 走 DashScope text-embedding-v3（key 优先 ``QWEN_EMBEDDING_API_KEY``，回落 ``DASHSCOPE_API_KEY``）。

运行（在 qwenpaw env）::

    conda run -n qwenpaw python rag/ingest.py
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# 复用后端 settings（读 .env：embedding key / database_url / 模型名）
sys.path.insert(0, str(REPO_ROOT / "backend"))

import dashscope  # noqa: E402
import psycopg  # noqa: E402
from pgvector.psycopg import register_vector  # noqa: E402

from app.core.config import settings  # noqa: E402

DATA_DIR = REPO_ROOT / "data"
EMBED_DIM = 1024  # text-embedding-v3 默认 1024 维；与 poi_chunks.embedding vector(1024) 对齐
BATCH = 10  # 每批向量化条数（保守，避免单批 token 过大 / QPS 限制）

log = logging.getLogger("rag.ingest")


def _db_url() -> str:
    """settings.database_url 是 sqlalchemy 形式 ``postgresql+psycopg://...``；
    psycopg3 直连要剥掉 ``+psycopg``。"""
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def _api_key() -> str:
    key = settings.qwen_embedding_api_key or settings.dashscope_api_key
    if not key:
        raise SystemExit("✗ 没有 embedding key：请在 .env 填 QWEN_EMBEDDING_API_KEY 或 DASHSCOPE_API_KEY")
    return key


def _load_pois() -> list[dict]:
    pois = json.loads((DATA_DIR / "pois.json").read_text(encoding="utf-8"))["pois"]
    docs: list[dict] = []
    for p in pois:
        parts = [str(p.get(f, "")) for f in ("intro", "history", "architecture", "story", "observation_tips") if p.get(f)]
        text = "\n".join(parts).strip()
        if text:
            docs.append({
                "poi_id": p["id"],
                "name": p.get("name_zh", ""),
                "text": text,
                "source_type": p.get("source_type", "ai"),
            })
    return docs


def embed_batch(texts: list[str], api_key: str) -> list[list[float]]:
    """一批文本 → 向量列表（按输入顺序）。失败抛异常。

    不显式传 dimension：text-embedding-v3 默认 1024，与表对齐；入库前有探针校验维度。
    """
    resp = dashscope.TextEmbedding.call(
        model=settings.qwen_embedding_model,
        input=texts,
        api_key=api_key,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"embedding 失败：{resp.code} {resp.message}")
    embs = sorted(resp.output["embeddings"], key=lambda e: e["text_index"])
    return [e["embedding"] for e in embs]


def upsert(docs: list[dict], vectors: list[list[float]]) -> None:
    """全量覆盖写入（TRUNCATE + INSERT），保证可重复运行。"""
    with psycopg.connect(_db_url()) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("TRUNCATE poi_chunks;")
            for d, vec in zip(docs, vectors, strict=True):
                cur.execute(
                    """
                    INSERT INTO poi_chunks (poi_id, name, text, source_type, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (poi_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        text = EXCLUDED.text,
                        source_type = EXCLUDED.source_type,
                        embedding = EXCLUDED.embedding
                    """,
                    (d["poi_id"], d["name"], d["text"], d["source_type"], vec),
                )
        conn.commit()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    api_key = _api_key()
    docs = _load_pois()
    log.info("待入库 POI：%d 个", len(docs))
    if not docs:
        return 0

    # 先探一条：验证 key/模型/维度，避免白跑全部
    probe = embed_batch(["连接测试"], api_key)
    if len(probe[0]) != EMBED_DIM:
        raise SystemExit(f"✗ embedding 维度={len(probe[0])}，表是 vector({EMBED_DIM})，不一致")
    log.info("探针通过：模型=%s 维度=%d", settings.qwen_embedding_model, len(probe[0]))

    vectors: list[list[float]] = []
    for i in range(0, len(docs), BATCH):
        batch = docs[i:i + BATCH]
        vectors.extend(embed_batch([d["text"] for d in batch], api_key))
        log.info("已向量化 %d/%d", min(i + BATCH, len(docs)), len(docs))
        time.sleep(0.15)  # 轻微限速，避免触发 QPS

    upsert(docs, vectors)
    print(f"✓ 已入库 {len(docs)} 个 POI 到 poi_chunks（pgvector）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
