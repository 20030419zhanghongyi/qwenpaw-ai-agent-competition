#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Revised Report Figures Generator for Macau AI Guide Project
Three compact information modules replacing five independent charts.
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# =============================================================================
# STYLE CONFIGURATION
# =============================================================================

BG_COLOR = "#FFFFFF"
TEXT_DARK = "#4A3B32"
TEXT_MUTED = "#8C7E72"
GRID_COLOR = "#E5E0D8"
PRIMARY_BAR = "#B8D2C8"
ACCENT_BAR = "#62AAA7"
LIGHT_TINT = "#F0F5F3"
DIVIDER_COLOR = "#DDD7CF"

REPORT_DPI = 300


def detect_chinese_font():
    """Auto-detect available Chinese font."""
    candidates = [
        "STFangsong", "华文仿宋", "FangSong", "仿宋", "FZFangSong-Z02",
        "Songti SC", "SimSun", "宋体",
        "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC",
        "Source Han Sans SC", "WenQuanYi Micro Hei", "SimHei",
        "Arial Unicode MS",
    ]
    available = [f.name for f in fm.fontManager.ttflist]
    for c in candidates:
        if c in available:
            return c
    return "sans-serif"


def apply_style():
    """Apply unified report style."""
    font = detect_chinese_font()
    plt.rcParams.update({
        "font.family": [font, "sans-serif"],
        "font.size": 9,
        "axes.facecolor": BG_COLOR,
        "figure.facecolor": BG_COLOR,
        "axes.edgecolor": GRID_COLOR,
        "axes.labelcolor": TEXT_DARK,
        "text.color": TEXT_DARK,
        "xtick.color": TEXT_MUTED,
        "ytick.color": TEXT_MUTED,
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
        "figure.dpi": REPORT_DPI,
    })


def save(fig, basename, out_dir):
    """Save PNG and SVG."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{basename}.png"
    svg = out_dir / f"{basename}.svg"
    fig.savefig(png, dpi=REPORT_DPI, bbox_inches="tight", facecolor=BG_COLOR)
    fig.savefig(svg, format="svg", bbox_inches="tight", facecolor=BG_COLOR)
    print(f"  Saved: {png.name}, {svg.name}")


# =============================================================================
# DATA
# =============================================================================

# Figure 1
SAMPLE = {
    "高赞笔记": ("100", "条"),
    "用户评论": ("751", "条"),
    "累计点赞": ("10.5", "万"),
    "累计收藏": ("11.4", "万"),
}
CORE_KEYWORDS = {
    "攻略": (167, "高频出现于高赞笔记内容中"),
    "路线": (63, "反映游客对行程安排的关注"),
}

# Figure 2
PAIN_POINTS = [
    {
        "value": 89,
        "label": "信息获取困惑",
        "keywords": "怎么 / 去哪 / 不知道 / 不懂",
        "response": "个性化行程生成",
        "accent": True,
    },
    {
        "value": 84,
        "label": "路线与体力负担",
        "keywords": "步行 / 累 / 回头路 / 暴走",
        "response": "轻量化路线优化",
        "accent": True,
    },
    {
        "value": 60,
        "label": "文化理解需求",
        "keywords": "历史 / 文化 / 背景 / 故事",
        "response": "场景化文化讲解",
        "accent": False,
    },
    {
        "value": 34,
        "label": "人流拥挤压力",
        "keywords": "排队 / 人多 / 拥挤 / 爆满",
        "response": "避峰路线建议",
        "accent": False,
    },
]

# Figure 3
ROUTE_DATA = [
    (57, "步行"), (15, "累"), (7, "回头路"), (5, "暴走"),
]
CULTURE_DATA = [
    (22, "历史"), (11, "文化"), (9, "为什么"), (7, "介绍"),
    (6, "背景"), (4, "故事"), (1, "看不懂"),
]


# =============================================================================
# FIGURE 1
# =============================================================================

def fig01():
    apply_style()
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Title
    fig.suptitle("调研样本与核心需求概览", fontsize=12, fontweight="bold",
                 color=TEXT_DARK, y=0.97)
    ax.text(5, 8.9, "数据来源：小红书“澳门旅游攻略”关键词，覆盖 2023–2025 年",
            ha="center", va="center", fontsize=7.5, color=TEXT_MUTED)

    # Upper: four compact cards
    cards = list(SAMPLE.items())
    card_w = 2.0
    gap = 0.25
    start_x = (10 - (4 * card_w + 3 * gap)) / 2
    y_card = 5.6

    for i, (label, (num, unit)) in enumerate(cards):
        x = start_x + i * (card_w + gap)
        rect = mpatches.FancyBboxPatch(
            (x, y_card), card_w, 2.2,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=BG_COLOR, edgecolor=GRID_COLOR, linewidth=1.0,
        )
        ax.add_patch(rect)
        ax.text(x + card_w / 2, y_card + 1.45, num,
                ha="center", va="center", fontsize=17, fontweight="bold",
                color=ACCENT_BAR)
        ax.text(x + card_w / 2 + 0.45, y_card + 1.45, unit,
                ha="left", va="center", fontsize=8.5, color=TEXT_MUTED)
        ax.text(x + card_w / 2, y_card + 0.55, label,
                ha="center", va="center", fontsize=8.5, color=TEXT_DARK)

    # Divider
    ax.plot([1, 9], [4.9, 4.9], color=DIVIDER_COLOR, linewidth=0.8, zorder=1)

    # Lower: core keywords
    ax.text(5, 4.3, "核心需求关键词（高赞笔记标题与正文中出现频次）",
            ha="center", va="center", fontsize=8, color=TEXT_MUTED)

    kw_items = list(CORE_KEYWORDS.items())
    block_w = 3.6
    gap_kw = 0.8
    start_x_kw = (10 - (2 * block_w + gap_kw)) / 2
    y_kw = 2.0

    for i, (kw, (val, desc)) in enumerate(kw_items):
        x = start_x_kw + i * (block_w + gap_kw)
        # Light background block
        rect = mpatches.FancyBboxPatch(
            (x, y_kw), block_w, 2.0,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=LIGHT_TINT, edgecolor="none",
        )
        ax.add_patch(rect)
        ax.text(x + block_w / 2, y_kw + 1.35, kw,
                ha="center", va="center", fontsize=10.5, fontweight="bold",
                color=TEXT_DARK)
        ax.text(x + block_w / 2, y_kw + 0.85, f"{val} 次",
                ha="center", va="center", fontsize=13, fontweight="bold",
                color=ACCENT_BAR)
        ax.text(x + block_w / 2, y_kw + 0.35, desc,
                ha="center", va="center", fontsize=7.5, color=TEXT_MUTED)

    return fig


# =============================================================================
# FIGURE 2
# =============================================================================

def fig02():
    apply_style()
    fig, ax = plt.subplots(figsize=(7.0, 3.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    fig.suptitle("游客游览问题相关表达频次与设计方向", fontsize=12,
                 fontweight="bold", color=TEXT_DARK, y=0.97)

    n = len(PAIN_POINTS)
    col_w = 2.15
    gap = 0.15
    start_x = (10 - (n * col_w + (n - 1) * gap)) / 2
    y_top = 8.2
    col_h = 5.8

    for i, item in enumerate(PAIN_POINTS):
        x = start_x + i * (col_w + gap)
        color = ACCENT_BAR if item["accent"] else PRIMARY_BAR

        # Main card
        rect = mpatches.FancyBboxPatch(
            (x, y_top - col_h), col_w, col_h,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            facecolor=BG_COLOR, edgecolor=GRID_COLOR, linewidth=0.8,
        )
        ax.add_patch(rect)

        # Value
        ax.text(x + col_w / 2, y_top - 0.9, str(item["value"]),
                ha="center", va="center", fontsize=18, fontweight="bold",
                color=color)
        ax.text(x + col_w / 2, y_top - 1.7, item["label"],
                ha="center", va="center", fontsize=9, fontweight="bold",
                color=TEXT_DARK)

        # Keywords
        ax.text(x + col_w / 2, y_top - 2.6, item["keywords"],
                ha="center", va="center", fontsize=7.5, color=TEXT_MUTED)

        # Response section (light tint background)
        resp_h = 1.4
        resp_y = y_top - col_h + 0.05
        resp_rect = mpatches.FancyBboxPatch(
            (x + 0.05, resp_y), col_w - 0.1, resp_h,
            boxstyle="round,pad=0.01,rounding_size=0.06",
            facecolor=LIGHT_TINT, edgecolor="none",
        )
        ax.add_patch(resp_rect)
        ax.text(x + col_w / 2, resp_y + resp_h / 2 + 0.25, "对应设计方向",
                ha="center", va="center", fontsize=6.5, color=TEXT_MUTED)
        ax.text(x + col_w / 2, resp_y + resp_h / 2 - 0.2, item["response"],
                ha="center", va="center", fontsize=7.5, fontweight="bold",
                color=TEXT_DARK)

    # Footnote
    ax.text(5, 1.5, "注：统计单位为相关表达出现频次；同一条评论可能涉及多个类别。",
            ha="center", va="center", fontsize=7, color=TEXT_MUTED)

    return fig


# =============================================================================
# FIGURE 3
# =============================================================================

def fig03():
    apply_style()
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    fig.suptitle("核心功能的数据依据", fontsize=12, fontweight="bold",
                 color=TEXT_DARK, y=0.97)

    left_x = 0.8
    right_x = 5.3
    col_w = 3.9
    y_start = 8.2

    # Vertical divider
    ax.plot([5.0, 5.0], [1.8, 8.6], color=DIVIDER_COLOR, linewidth=0.8)

    def draw_col(x, title, subtitle, total, data, hint):
        # Column title
        ax.text(x + col_w / 2, y_start, title,
                ha="center", va="center", fontsize=9.5, fontweight="bold",
                color=TEXT_DARK)
        ax.text(x + col_w / 2, y_start - 0.55, subtitle,
                ha="center", va="center", fontsize=8, color=TEXT_MUTED)
        ax.text(x + col_w / 2, y_start - 1.1, f"{total} 次",
                ha="center", va="center", fontsize=14, fontweight="bold",
                color=ACCENT_BAR)

        # Data list
        y_pos = y_start - 2.0
        for val, kw in data:
            num_color = ACCENT_BAR if val == max(v for v, _ in data) else TEXT_DARK
            ax.text(x + 0.3, y_pos, f"{val} 次",
                    ha="left", va="center", fontsize=9, fontweight="bold",
                    color=num_color)
            ax.text(x + 1.4, y_pos, kw,
                    ha="left", va="center", fontsize=9, color=TEXT_DARK)
            y_pos -= 0.62

        # Hint box
        hint_y = y_pos - 0.1
        hint_h = 0.9
        rect = mpatches.FancyBboxPatch(
            (x + 0.1, hint_y), col_w - 0.2, hint_h,
            boxstyle="round,pad=0.01,rounding_size=0.05",
            facecolor=LIGHT_TINT, edgecolor="none",
        )
        ax.add_patch(rect)
        ax.text(x + col_w / 2, hint_y + hint_h / 2, hint,
                ha="center", va="center", fontsize=7, color=TEXT_MUTED)

    draw_col(left_x, "智能路线规划的数据依据",
             "路线与体力相关表达", 84, ROUTE_DATA,
             "设计提示：减少重复步行与体力负担")

    draw_col(right_x, "场景化文化讲解的数据依据",
             "历史文化相关表达", 60, CULTURE_DATA,
             "设计提示：帮助游客理解旧区历史文化")

    # Footnote
    ax.text(5, 1.2, "注：“步行”表示游客对步行路线及距离的关注，不完全等同于负面评价。",
            ha="center", va="center", fontsize=7, color=TEXT_MUTED)
    ax.text(5, 0.7, "统计单位为相关表达出现频次；同一条评论可能涉及多个类别。",
            ha="center", va="center", fontsize=7, color=TEXT_MUTED)

    return fig


# =============================================================================
# MAIN
# =============================================================================

def main():
    base = Path(__file__).resolve().parent.parent
    out = base / "figures_revised"

    print("=" * 60)
    print("Generating Revised Report Figures")
    print(f"Output: {out}")
    print(f"Font: {detect_chinese_font()}")
    print("=" * 60)

    f1 = fig01()
    save(f1, "fig01_research_and_core_needs", out)
    plt.close(f1)

    f2 = fig02()
    save(f2, "fig02_pain_points_and_product_response", out)
    plt.close(f2)

    f3 = fig03()
    save(f3, "fig03_evidence_for_core_functions", out)
    plt.close(f3)

    print("\nAll revised figures generated successfully.")


if __name__ == "__main__":
    main()
