"""离线批量：用 QwenPaw 给「瘦 POI」补文化内容。

对 `data/pois.json` 里 5 个文化字段为空的 POI（intro/history/architecture/story/
observation_tips），调本地 QwenPaw（默认 `default` agent；待 `guide` agent 建好后
用 `--agent guide`），让模型按统一 schema 补全，并：

- 填回 5 个字段；
- `source_type` 置 `"ai"`（POI 模型里 source_type 的用途正是「AI 伦理透明度：区分
  内容来源」，见 `backend/app/models/poi.py`）；
- `verify_status` 置 `"AI生成·待核验"`（人工/官方核验前不当作权威）；
- 每条另写一行审计日志到 `data/legacy/guide_enrichment_log.jsonl`（置信度/token/
  延迟/状态），`pois.json` 本身保持 schema 干净。

纪律（对齐 `skills/macau-guide/SKILL.md`）：不编史料、易变信息低置信且「以现场为准」、
信息极度匮乏时如实说明。

幂等 + 可续跑：intro 已非空的 POI 自动跳过（14 条人工富化 + 之前已生成的），中途
Ctrl-C / 崩溃后重跑即从断点继续（每条生成后立即原子写回）。

用法：
    # 烟测 2 条（含一名景 + 一冷门），看质量
    python scripts/generate_guide_content.py --limit 2 --sleep 0.6

    # 指定 POI
    python scripts/generate_guide_content.py --only poi_0001 poi_0043

    # 全量（耗 token，建议睡前跑；中途可 Ctrl-C 续跑）
    python scripts/generate_guide_content.py --sleep 0.6

    # guide agent 建好后改走 guide
    python scripts/generate_guide_content.py --agent guide
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# 复用后端 QwenPaw 客户端
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.agents.qwenpaw_client import QwenPawClient, QwenPawError  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
POIS_PATH = REPO / "data" / "pois.json"
LOG_PATH = REPO / "data" / "legacy" / "guide_enrichment_log.jsonl"

# 5 个要补的文化字段
CULTURAL_FIELDS = ("intro", "history", "architecture", "story", "observation_tips")


# ---- prompt -----------------------------------------------------------------

def build_prompt(poi: dict) -> str:
    name = poi.get("name_zh") or poi["id"]
    name_pt = (poi.get("name_pt") or "").strip() or "无"
    district = poi.get("district") or "未标注"
    theme = "、".join(poi.get("theme") or []) or "无"
    amap = poi.get("amap") or {}
    amap_type = amap.get("type") or "无"
    amap_addr = amap.get("address") or "无"
    return f"""你是澳门文旅知识编辑。请根据下方景点信息，为它补全结构化文化资料，用于导览知识库。

【景点】
- 中文名：{name}
- 葡文名：{name_pt}
- 所属堂区：{district}
- 主题标签：{theme}
- 高德类型：{amap_type}
- 地址：{amap_addr}

【输出要求】
1. 只输出一个 JSON 对象，第一个字符必须是 {{，不要 markdown 代码围栏、不要任何解释文字。
2. 字段含义与字数：
   - intro：基本介绍（是什么、最标志性的一点），1-2 句，≤60 字
   - history：历史背景（建造/形成年代与由来）
   - architecture：建筑或景观特色（风格、材质、布局）
   - story：相关文化故事或趣闻，1 句；无可靠内容就给空字符串 ""
   - observation_tips：游览/拍摄建议，1 句
   - confidence：你对以上事实准确度的把握，0-1 两位小数
3. 纪律（重要）：
   - 不编史料：信息不足的字段写概括性描述或留空，并把 confidence 相应调低，绝不杜撰具体年份/人名。
   - 易变信息（开放时间/票价/活动/节假日）一律不给具体时间表；如需提及写「以现场为准」。
   - 若信息极度匮乏、或你不确定该地点是什么，intro 如实说明「公开资料有限」，confidence ≤ 0.4。
4. 字段值里若要引用或强调名称，一律用『』，**不要**用 ""，以免破坏 JSON。
5. 全部用简体中文。

【输出 JSON】
{{"intro":"","history":"","architecture":"","story":"","observation_tips":"","confidence":0.8}}"""


# ---- JSON 解析 --------------------------------------------------------------

import re  # noqa: E402  (salvage 用)

_ALL_FIELDS = list(CULTURAL_FIELDS) + ["confidence"]


def _strict_parse(text: str) -> dict | None:
    """严格 JSON：去围栏后 json.loads 第一个 {...}。"""
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s.split("\n", 1)[-1] if "\n" in s else s
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        obj = json.loads(s[start : end + 1])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def _salvage_fields(text: str) -> dict | None:
    """容错抽取：以「下一个字段名」为分隔逐字段截值，容忍值内嵌未转义引号
    （模型常把强调名写成 "大三巴" 这种）。无 intro 返回 None。"""
    if not text:
        return None
    # 定位每个 "field": 的位置
    positions: list[tuple[int, str]] = []
    for f in _ALL_FIELDS:
        m = re.search(r'"' + re.escape(f) + r'"\s*:\s*', text)
        if m:
            positions.append((m.end(), f))
    if not positions:
        return None
    positions.sort()
    out: dict = {}
    for i, (start, f) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        chunk = text[start:end]
        # 去掉末尾的 , } 及空白
        chunk = re.sub(r"[,}\s]+$", "", chunk).strip()
        if f == "confidence":
            m = re.match(r"-?\d+(?:\.\d+)?", chunk)
            if m:
                out[f] = float(m.group())
        else:
            v = chunk
            if v.startswith('"'):
                v = v[1:]
            if v.endswith('"'):
                v = v[:-1]
            v = v.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
            out[f] = v.strip()
    if not out.get("intro"):
        return None
    return out


def parse_json_obj(text: str) -> dict | None:
    """先严格解析；失败则容错逐字段抽取。"""
    return _strict_parse(text) or _salvage_fields(text)


def coerce_fields(obj: dict) -> dict | None:
    """校验并规整 5 个字段；至少 intro 非空才算可用。"""
    out = {}
    for f in CULTURAL_FIELDS:
        v = obj.get(f, "")
        out[f] = str(v).strip() if v is not None else ""
    if not out["intro"]:
        return None
    return out


# ---- 主流程 -----------------------------------------------------------------

def is_thin(poi: dict) -> bool:
    return not (poi.get("intro") or "").strip()


def atomic_write_pois(path: Path, doc: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(tmp, path)


def append_log(rec: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _call_one(poi: dict, qp: QwenPawClient, agent: str) -> tuple[dict | None, dict]:
    """【工作线程】只做网络调用 + 解析，**不改 poi、不写盘**，线程安全。
    返回 (fields|None, rec)。fields 非空表示可写入。"""
    pid = poi["id"]
    name = poi.get("name_zh") or pid
    prompt = build_prompt(poi)
    t0 = time.perf_counter()
    rec: dict = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "id": pid,
        "name": name,
        "district": poi.get("district"),
        "agent": agent,
    }
    try:
        raw = qp.ask(agent, prompt, session_id=f"guide-enrich-{pid}")
    except QwenPawError as exc:
        rec.update({"status": "call_failed", "error": str(exc)[:200],
                    "latency_ms": int((time.perf_counter() - t0) * 1000)})
        return None, rec

    latency_ms = int((time.perf_counter() - t0) * 1000)
    obj = parse_json_obj(raw)
    fields = coerce_fields(obj) if obj else None
    if not fields:
        # 诊断：区分「内嵌引号/格式」失败 vs 「真的被截断」
        ends_ok = (raw or "").rstrip().endswith("}")
        rec.update({"status": "parse_failed", "latency_ms": latency_ms,
                    "raw_len": len(raw or ""), "ends_with_brace": ends_ok,
                    "raw_head": (raw or "")[:200]})
        return None, rec

    confidence = obj.get("confidence")
    try:
        confidence = round(float(confidence), 2)
    except (TypeError, ValueError):
        confidence = None
    rec.update({"status": "ok", "latency_ms": latency_ms,
                "confidence": confidence, "intro_head": fields["intro"][:60]})
    return fields, rec


def _apply_fields(poi: dict, fields: dict) -> None:
    """【主线程】把解析好的字段写回单条 poi（in place）。只在主线程调用，避免竞争。"""
    for f in CULTURAL_FIELDS:
        poi[f] = fields[f]
    poi["source_type"] = "ai"
    poi["verify_status"] = "AI生成·待核验"


def main() -> None:
    ap = argparse.ArgumentParser(description="用 QwenPaw 批量补 POI 文化内容（并发）")
    ap.add_argument("--agent", default="default", help="调用的 agent id（default/guide）")
    ap.add_argument("--workers", type=int, default=6,
                    help="并发线程数（瓶颈是单条 ~25s 延迟，6≈4-6x 提速）")
    ap.add_argument("--limit", type=int, default=None, help="只处理前 N 条瘦 POI（烟测用）")
    ap.add_argument("--only", nargs="*", default=None, help="只处理指定 id（覆盖 --limit）")
    ap.add_argument("--dry-run", action="store_true", help="只打印 prompt，不调用、不写盘")
    args = ap.parse_args()

    doc = json.loads(POIS_PATH.read_text(encoding="utf-8"))
    pois: list[dict] = doc["pois"]

    if args.only:
        want = set(args.only)
        targets = [p for p in pois if p["id"] in want and is_thin(p)]
        skipped_non_thin = want - {p["id"] for p in targets}
        if skipped_non_thin:
            print(f"⚠ 跳过（已富化或不存在）：{sorted(skipped_non_thin)}")
    else:
        thin_all = [p for p in pois if is_thin(p)]
        targets = thin_all[: args.limit] if args.limit else thin_all

    print(f"=== guide enrich | agent={args.agent} | workers={args.workers} "
          f"| 待处理={len(targets)} | dry_run={args.dry_run} ===", flush=True)

    if args.dry_run:
        for p in targets[:3]:
            print("\n--- prompt ---")
            print(build_prompt(p))
        print(f"\n（dry-run，共 {len(targets)} 条，未调用、未写盘）")
        return

    qp = QwenPawClient()
    ok = fail = 0
    t_start = time.perf_counter()
    # 并发跑网络；apply/写盘/日志全部回主线程串行做（避免 pois.json 写竞争）
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        fut_to_poi = {pool.submit(_call_one, p, qp, args.agent): p for p in targets}
        done = 0
        for fut in as_completed(fut_to_poi):
            poi = fut_to_poi[fut]
            try:
                fields, rec = fut.result()
            except Exception as exc:  # 线程内未预期异常兜底
                rec = {"ts": datetime.now().isoformat(timespec="seconds"),
                       "id": poi["id"], "name": poi.get("name_zh", poi["id"]),
                       "status": "worker_error", "error": f"{type(exc).__name__}: {exc}"}
                fields = None
            append_log(rec)
            done += 1
            if rec["status"] == "ok" and fields:
                _apply_fields(poi, fields)  # 主线程写入，无竞争
                ok += 1
                flag = "✓"
                tail = f" conf={rec.get('confidence')} | {rec['intro_head']}"
            else:
                fail += 1
                flag = "✗"
                tail = f" {rec['status']}: {rec.get('error') or rec.get('raw_head','')}"
            print(f"[{done}/{len(targets)}] {flag} {poi['id']:12} "
                  f"{poi.get('name_zh','')[:14]:<14}{tail}", flush=True)
            # 每条回来即原子写回 → 中断后重跑即续跑
            atomic_write_pois(POIS_PATH, doc)

    elapsed = int(time.perf_counter() - t_start)
    print(f"\n完成：成功 {ok}，失败 {fail}，用时 {elapsed}s（{args.workers} 并发）。"
          f"已写回 {POIS_PATH}；审计日志 {LOG_PATH}", flush=True)


if __name__ == "__main__":
    main()
