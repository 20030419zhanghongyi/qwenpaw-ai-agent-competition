"""RAG 检索接口（Phase 3：pgvector 语义检索 + Phase 1 关键词回落）。

主路径：pgvector 向量语义 top-k（query embedding → 余弦相似 → 返回整 POI）。
回落：pgvector 未启用 / 库连不上 / store 空 → Phase 1 关键词粗检索，保证流程可跑。

被 backend 文化讲解 / 拍照识别讲解链路调用::

    from rag.retrieve import retrieve
    docs = retrieve("疯堂斜巷的历史", k=4)
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger("rag.retrieve")


# ────────────── Phase 1：关键词粗检索（fallback）──────────────

def _load_chunks() -> list[dict]:
    pois_path = REPO_ROOT / "data" / "pois.json"
    if not pois_path.exists():
        return []
    pois = json.loads(pois_path.read_text(encoding="utf-8"))["pois"]
    chunks: list[dict] = []
    for poi in pois:
        text = "\n".join(
            str(poi.get(f, "")) for f in ("intro", "history", "architecture", "story", "observation_tips")
        )
        chunks.append({
            "poi_id": poi["id"],
            "name": poi.get("name_zh", ""),
            "text": text,
            "source_type": poi.get("source_type", "official"),
        })
    return chunks


def _keyword_retrieve(query: str, k: int = 4) -> list[dict]:
    """Phase 1：字符重合度打分（仅供 pgvector 不可用时的 baseline）。"""
    chunks = _load_chunks()
    q = set(query.lower())
    scored = []
    for c in chunks:
        score = sum(1 for ch in c["text"] if ch.lower() in q) / max(len(c["text"]), 1)
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:k]]


# ────────────── POI 精确取料（讲解主路径用）──────────────

def _format_poi(p: dict) -> tuple[str, str]:
    """把一个 POI 整理成 (name, 带字段标签的结构化资料文本)，对齐 macau-guide 技能输入。"""
    lines = []
    for f in ("intro", "history", "architecture", "story", "observation_tips"):
        v = p.get(f)
        if v:
            lines.append(f"{f}: {v}")
    return p.get("name_zh", "") or p.get("name_en", ""), "\n".join(lines)


def get_poi_material(poi_name: str) -> tuple[str, str] | None:
    """按名字/id 精确 → 包含匹配 POI，返回 (name, 结构化资料)。找不到返回 None。

    讲解主路径用：candidate_poi 已点名时直接精确取整 POI 资料（不靠向量检索，最稳）；
    找不到时调用方再退到 ``retrieve()`` 向量兜底。
    """
    pois_path = REPO_ROOT / "data" / "pois.json"
    if not pois_path.exists():
        return None
    name = (poi_name or "").strip()
    if not name:
        return None
    pois = json.loads(pois_path.read_text(encoding="utf-8"))["pois"]
    # 1) 精确匹配（中/英/葡名 或 id）
    for p in pois:
        if name in {p.get("name_zh"), p.get("name_en"), p.get("name_pt"), p.get("id")}:
            return _format_poi(p)
    # 2) 包含匹配（candidate_poi 含 POI 名，或反之）
    for p in pois:
        nz = p.get("name_zh", "")
        if nz and (name in nz or nz in name):
            return _format_poi(p)
    return None


# ────────────── Phase 3：pgvector 语义检索 ─────────────

def _vector_retrieve(query: str, k: int = 4) -> list[dict]:
    """query → embedding → pgvector 余弦 top-k。失败抛异常（由 retrieve 捕获回落）。"""
    sys.path.insert(0, str(REPO_ROOT / "backend"))  # 延迟 import：回落路径不强依赖 backend
    from app.core.config import settings

    import dashscope
    import psycopg

    api_key = settings.qwen_embedding_api_key or settings.dashscope_api_key
    if not api_key:
        raise RuntimeError("no embedding key")

    resp = dashscope.TextEmbedding.call(model=settings.qwen_embedding_model, input=[query], api_key=api_key)
    if resp.status_code != 200:
        raise RuntimeError(f"embed query failed: {resp.code} {resp.message}")
    qvec = resp.output["embeddings"][0]["embedding"]
    # pgvector 字面量串：psycopg 默认把 list dump 成 array，<=> 算子认不出。
    # INSERT 有列类型上下文能自动转 vector，比较算子没有 → 手动拼 [..]::vector。
    qvec_str = "[" + ",".join(repr(x) for x in qvec) + "]"

    dburl = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dburl) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT poi_id, name, text, source_type, 1 - (embedding <=> %s::vector) AS score
                FROM poi_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (qvec_str, qvec_str, k),
            )
            rows = cur.fetchall()
    return [
        {"poi_id": r[0], "name": r[1], "text": r[2], "source_type": r[3], "score": float(r[4])}
        for r in rows
    ]


def retrieve(query: str, k: int = 4) -> list[dict]:
    """语义检索（pgvector）；不可用则回落关键词粗检索。永不抛穿。"""
    try:
        sys.path.insert(0, str(REPO_ROOT / "backend"))
        from app.core.config import settings
        if settings.pgvector_enabled:
            res = _vector_retrieve(query, k)
            if res:
                return res
            log.info("向量库为空，回落关键词检索")
    except Exception as exc:  # noqa: BLE001 - pg 连不上 / embed 失败 / 解析错，一律回落
        log.info("向量检索失败，回落关键词检索：%s", exc)
    return _keyword_retrieve(query, k)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    q = " ".join(sys.argv[1:]) or "疯堂斜巷 葡式碎石 历史"
    print(f"query: {q}")
    for doc in retrieve(q):
        score = doc.get("score")
        s = f" {score:.3f}" if score is not None else ""
        print(f"- {doc['name']} ({doc.get('source_type')}){s}  {doc['text'][:60]}")
