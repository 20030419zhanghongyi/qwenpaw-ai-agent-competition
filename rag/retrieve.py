"""RAG 检索接口（Phase 3 实现，Phase 1 占位）。

被 backend/agents/ 文化讲解 Agent 与图像识别讲解 Agent 调用：
    from rag.retrieve import retrieve
    docs = retrieve("疯堂斜巷的历史", k=4)

Phase 1 返回基于关键词的内存粗检索，保证流程可跑；
Phase 3 替换为 pgvector 向量检索。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
log = logging.getLogger("rag.retrieve")


def _load_chunks() -> list[dict]:
    pois_path = DATA_DIR / "pois.json"
    if not pois_path.exists():
        return []
    pois = json.loads(pois_path.read_text(encoding="utf-8"))["pois"]
    chunks: list[dict] = []
    for poi in pois:
        text = "\n".join(
            str(poi.get(f, "")) for f in ("intro", "history", "architecture", "story", "observation_tips")
        )
        chunks.append({"poi_id": poi["id"], "name": poi["name_zh"], "text": text, "source_type": poi.get("source_type", "official")})
    return chunks


def retrieve(query: str, k: int = 4) -> list[dict]:
    """Phase 1：关键词粗检索。Phase 3：换 pgvector 向量检索。"""
    chunks = _load_chunks()
    q = set(query.lower())
    scored = []
    for c in chunks:
        # 简单字符重合度打分，仅供流程演示
        score = sum(1 for ch in c["text"] if ch.lower() in q) / max(len(c["text"]), 1)
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:k]]


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "疯堂斜巷 葡式碎石 历史"
    print(f"query: {q}")
    for doc in retrieve(q):
        print("-", doc["name"], "(", doc["source_type"], ")", doc["text"][:60])
