"""跑批对比 + 出图（P2 调优证据，截图节点⑥）。

读 harness/results/scores_<run>.json 一个或多个 run，渲染自包含 HTML（SVG 柱状图 +
逐 case 表）。无外部依赖，浏览器打开即可截图。

用法：
    python -m app.eval.compare                          # 最近一个 run 的逐 case 图
    python -m app.eval.compare --runs rules-baseline agent-v1   # before/after 对比
    python -m app.eval.compare --all                    # 全部 run 汇总

调优叙事：rules-baseline（before）→ 改 SKILL.md/启用 agent → agent-v1（after），
两两对比看哪类 case 涨分，即「调优过」的最强证据。
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from app.core.config import settings

RESULTS_DIR = settings.repo_root / "harness" / "results"

# 克制、色盲友好的双色调（before 灰 / after 强调），其余用中性
COLOR_BEFORE = "#9aa4b2"
COLOR_AFTER = "#2f6df6"
COLOR_SINGLE = "#2f6df6"


def _load(run_id: str) -> dict:
    path = RESULTS_DIR / f"scores_{run_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _list_runs() -> list[str]:
    return sorted(p.stem[len("scores_") :] for p in RESULTS_DIR.glob("scores_*.json"))


def _bar(x: float, y: float, w: float, h: float, color: str, label: str, value: str) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{color}" rx="2"/>'
        f'<text x="{(x + w + 6):.1f}" y="{(y + h / 2 + 4):.1f}" '
        f'font-size="12" fill="#334">{html.escape(value)}</text>'
        f'<title>{html.escape(label)}</title>'
    )


def render_single(run: dict) -> str:
    """单个 run：逐 case 横向柱状图（按 category 着色）。"""
    cases = run["cases"]
    row_h, gap, top, left, max_w = 26, 6, 60, 220, 420
    h = top + len(cases) * (row_h + gap) + 40
    rows = []
    rows.append(f'<text x="{left}" y="30" font-size="16" font-weight="600" fill="#1a1f2e">'
                f'评测 run：{html.escape(run["run_id"])} — overall {run["overall"]:.2f}</text>')
    rows.append(f'<text x="{left}" y="50" font-size="12" fill="#6b7280">'
                f'route {run["by_category"].get("route")} · guide {run["by_category"].get("guide")} · n={run["n"]}</text>')
    for i, c in enumerate(cases):
        y = top + i * (row_h + gap)
        score = c["score"]
        col = "#3aa6" if c["category"] == "route" else "#f59e0b"
        rows.append(f'<text x="0" y="{y + row_h - 8:.1f}" font-size="12" fill="#334">'
                    f'{html.escape(c["id"] + " " + c["category"])}</text>')
        rows.append(_bar(left, y, max_w * score, row_h, col,
                         f'{c["id"]} {score:.2f} ({c["passed"]}/{c["total"]})', f'{score:.2f}'))
    return _wrap("评测分数", f'<svg viewBox="0 0 700 {h}" width="100%">{"".join(rows)}</svg>')


def render_compare(a: dict, b: dict) -> str:
    """两个 run：逐 case before/after 分组柱 + overall 摘要。"""
    by_id_a = {c["id"]: c["score"] for c in a["cases"]}
    by_id_b = {c["id"]: c["score"] for c in b["cases"]}
    ids = list(dict.fromkeys(list(by_id_a) + list(by_id_b)))

    row_h, gap, top, left, max_w, bw = 22, 10, 90, 150, 360, 16
    h = top + len(ids) * (row_h + gap) + 70
    rows = []
    delta = b["overall"] - a["overall"]
    sign = "↑" if delta >= 0 else "↓"
    rows.append(f'<text x="{left}" y="28" font-size="16" font-weight="600" fill="#1a1f2e">'
                f'调优 before→after：{html.escape(a["run_id"])} → {html.escape(b["run_id"])}</text>')
    rows.append(f'<text x="{left}" y="50" font-size="13" fill="#334">'
                f'overall {a["overall"]:.2f} → {b["overall"]:.2f} '
                f'<tspan fill="{("#16a34a" if delta >= 0 else "#dc2626")}" font-weight="600">'
                f'{sign} {abs(delta):+.2f}</tspan></text>')
    rows.append(f'<rect x="{left}" y="58" width="{bw}" height="10" fill="{COLOR_BEFORE}"/>'
                f'<text x="{left + bw + 6}" y="67" font-size="11" fill="#6b7280">before</text>'
                f'<rect x="{left + 90}" y="58" width="{bw}" height="10" fill="{COLOR_AFTER}"/>'
                f'<text x="{left + 90 + bw + 6}" y="67" font-size="11" fill="#6b7280">after</text>')

    for i, cid in enumerate(ids):
        y = top + 30 + i * (row_h + gap)
        sa, sb = by_id_a.get(cid, 0), by_id_b.get(cid, 0)
        rows.append(f'<text x="0" y="{y + row_h - 6:.1f}" font-size="12" fill="#334">{html.escape(cid)}</text>')
        rows.append(_bar(left, y, max_w * sa, 8, COLOR_BEFORE, f'{cid} before {sa:.2f}', f'{sa:.2f}'))
        rows.append(_bar(left, y + 11, max_w * sb, 8, COLOR_AFTER, f'{cid} after {sb:.2f}', f'{sb:.2f}'))

    return _wrap("调优 before/after", f'<svg viewBox="0 0 640 {h}" width="100%">{"".join(rows)}</svg>')


def _wrap(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="zh"><head><meta charset="utf-8">'
        f'<title>{html.escape(title)}</title>'
        '<style>body{font-family:-apple-system,"PingFang SC",system-ui,sans-serif;'
        'background:#fff;color:#1a1f2e;margin:24px}'
        'svg{font-family:inherit}</style></head><body>'
        f'<h2 style="margin-top:0">{html.escape(title)}</h2>{body}</body></html>'
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="跑批对比/出图")
    ap.add_argument("--runs", nargs="*", default=None, help="1 个 run 或 2 个 run（before after）")
    ap.add_argument("--all", action="store_true", help="汇总全部 run")
    args = ap.parse_args()

    runs = args.runs
    if args.all or not runs:
        all_runs = _list_runs()
        if not all_runs:
            print("没有 scores_*.json，先跑 runner。"); return
        if not runs:
            runs = [all_runs[-1]]  # 默认最近一个

    if len(runs) == 1:
        out = render_single(_load(runs[0]))
        name = f"chart_{runs[0]}.html"
    else:
        a, b = runs[0], runs[-1]
        out = render_compare(_load(a), _load(b))
        name = f"compare_{a}_vs_{b}.html"

    path = RESULTS_DIR / name
    path.write_text(out, encoding="utf-8")
    print(f"→ {path}")
    print(f"  浏览器打开即可截图（file://{path}）")


if __name__ == "__main__":
    main()
