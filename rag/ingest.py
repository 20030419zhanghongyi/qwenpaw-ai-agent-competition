"""RAG 入库脚本（Phase 1 占位 / Phase 3 实现）。

职责：把 data/ 下的 POI 文化讲解、街区故事、典型游客困惑表述
分块、embedding，写入向量库（pgvector）。

Phase 1：仅定义流程与数据源，留 TODO。
Phase 3：实现真实 embedding + 入库，并在 backend/agents/ 文化讲解 Agent 中检索。

运行：python rag/ingest.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

log = logging.getLogger("rag.ingest")


def load_source_documents() -> list[dict]:
    """从 data/pois.json 构造待入库的文档块。

    每个 POI 拆成若干 chunk（intro / history / architecture / story），
    便于讲解 Agent 精准检索。返回 {id, poi_id, field, text, source_type} 列表。
    """
    pois_path = DATA_DIR / "pois.json"
    if not pois_path.exists():
        log.warning("data/pois.json 不存在，跳过。")
        return []

    pois = json.loads(pois_path.read_text(encoding="utf-8"))["pois"]
    chunks: list[dict] = []
    for poi in pois:
        for field in ("intro", "history", "architecture", "story", "observation_tips"):
            text = poi.get(field, "")
            if text:
                chunks.append(
                    {
                        "id": f"{poi['id']}__{field}",
                        "poi_id": poi["id"],
                        "field": field,
                        "text": text,
                        "source_type": poi.get("source_type", "official"),
                    }
                )
    return chunks


def embed(texts: list[str]) -> list[list[float]]:
    """TODO(Phase 3)：调 DashScope text-embedding-v3 生成向量。

    示例（待 key 配置后启用）：
        import dashscope
        resp = dashscope.TextEmbedding.call(
            model=os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v3"),
            input=texts,
            api_key=os.getenv("DASHSCOPE_API_KEY"),
        )
        return [d["embedding"] for d in resp.output["embeddings"]]
    """
    raise NotImplementedError("Phase 3 实现：接 DashScope embedding。")


def upsert_to_store(chunks: list[dict], vectors: list[list[float]]) -> None:
    """TODO(Phase 3)：写入 pgvector。schema 示例：
        create table poi_chunks (
          id text primary key, poi_id text, field text,
          text text, source_type text, embedding vector(1024)
        );
    """
    raise NotImplementedError("Phase 3 实现：写入 pgvector。")


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    chunks = load_source_documents()
    log.info("待入库 chunk 数：%d", len(chunks))
    if not chunks:
        return 0

    # Phase 3 取消下面的注释并实现 embed / upsert_to_store。
    print(f"✓ 解析出 {len(chunks)} 个 chunk，等待 Phase 3 实现 embedding + 入库。")
    print("  样例：", chunks[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
