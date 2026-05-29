#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Figures Generator for Macau AI Guide Project
Generates publication-ready charts in a unified formal report style.
"""

import os
import sys
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
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
SECONDARY_BAR = "#D8DEE5"
ALERT_BAR = "#DDA56A"

REPORT_WIDTH = 6.3  # inches, suitable for A4 portrait
REPORT_DPI = 300


def detect_chinese_font():
    """Auto-detect available Chinese font.
    Priority: FangSong variants > Songti (serif fallback) > system defaults.
    """
    candidates = [
        # FangSong / 仿宋 (preferred)
        "STFangsong",
        "华文仿宋",
        "FangSong",
        "仿宋",
        "FZFangSong-Z02",
        # Songti / 宋体 (serif fallback, closest to FangSong on macOS)
        "Songti SC",
        "SimSun",
        "宋体",
        # System defaults
        "PingFang SC",
        "Microsoft YaHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "WenQuanYi Micro Hei",
        "SimHei",
        "Arial Unicode MS",
    ]
    available = [f.name for f in fm.fontManager.ttflist]
    for c in candidates:
        if c in available:
            return c
    return "sans-serif"


def apply_report_style():
    """Apply unified report style to matplotlib."""
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
        "axes.spines.left": True,
        "axes.spines.bottom": True,
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "figure.dpi": REPORT_DPI,
    })


def save_both(fig, basename, output_dir):
    """Save figure as PNG and SVG."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / f"{basename}.png"
    svg_path = output_dir / f"{basename}.svg"
    fig.savefig(png_path, dpi=REPORT_DPI, bbox_inches="tight", facecolor=BG_COLOR)
    fig.savefig(svg_path, format="svg", bbox_inches="tight", facecolor=BG_COLOR)
    print(f"  Saved: {png_path.name}, {svg_path.name}")


# =============================================================================
# DATA (verified from xlsx raw data)
# =============================================================================

DATA_SOURCE = "background/raw_data/xhs/xhs_search_20260528_204244.xlsx"

# Figure 1: Research Overview
FIG1_DATA = {
    "高赞笔记": 100,
    "用户评论": 751,
    "点赞": "10.5万",
    "收藏": "11.4万",
}

# Figure 2: Route & Guide Demand (from note titles + descriptions only)
FIG2_DATA = {
    "攻略": 167,
    "路线": 63,
}

# Figure 3: Pain Point Categories (from all text: notes + comments)
FIG3_DATA = {
    "信息获取困惑": 89,      # 怎么61 + 去哪14 + 不会8 + 不知道5 + 不懂1
    "路线与体力负担": 84,    # 步行57 + 累15 + 回头路7 + 暴走5
    "文化理解需求": 60,      # 历史22 + 文化11 + 为什么9 + 介绍7 + 背景6 + 故事4 + 看不懂1
    "人流拥挤压力": 34,      # 排队25 + 人多5 + 拥挤2 + 爆满2
}
FIG3_KEYWORDS = {
    "信息获取困惑": "怎么 / 去哪 / 不会 / 不知道 / 不懂",
    "路线与体力负担": "步行 / 累 / 回头路 / 暴走",
    "文化理解需求": "历史 / 文化 / 为什么 / 介绍 / 背景 / 故事",
    "人流拥挤压力": "排队 / 人多 / 拥挤 / 爆满",
}

# Figure 4: Physical & Route Burden Breakdown
FIG4_DATA = {
    "步行": 57,
    "累": 15,
    "回头路": 7,
    "暴走": 5,
}

# Figure 5: Cultural Understanding Breakdown
FIG5_DATA = {
    "历史": 22,
    "文化": 11,
    "为什么": 9,
    "介绍": 7,
    "背景": 6,
    "故事": 4,
    "看不懂": 1,
}


# =============================================================================
# FIGURE GENERATORS
# =============================================================================

def fig01_research_overview(output_dir):
    """Figure 1: Research Sample Overview — card-style summary."""
    apply_report_style()

    fig, ax = plt.subplots(figsize=(REPORT_WIDTH, 3.0))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    cards = [
        ("100", "条", "高赞笔记"),
        ("751", "条", "用户评论"),
        ("10.5", "万", "累计点赞"),
        ("11.4", "万", "累计收藏"),
    ]
    card_w = 2.1
    gap = 0.3
    start_x = (10 - (4 * card_w + 3 * gap)) / 2

    for i, (num, unit, label) in enumerate(cards):
        x = start_x + i * (card_w + gap)
        rect = plt.Rectangle(
            (x, 2.5), card_w, 5,
            facecolor=BG_COLOR,
            edgecolor=GRID_COLOR,
            linewidth=1.2,
            zorder=1
        )
        ax.add_patch(rect)

        # Number
        ax.text(x + card_w / 2, 6.2, num,
                ha="center", va="center",
                fontsize=18, fontweight="bold",
                color=ACCENT_BAR, zorder=2)
        # Unit
        ax.text(x + card_w / 2 + 0.5, 6.2, unit,
                ha="left", va="center",
                fontsize=9, color=TEXT_MUTED, zorder=2)
        # Label
        ax.text(x + card_w / 2, 3.8, label,
                ha="center", va="center",
                fontsize=9, color=TEXT_DARK, zorder=2)

    # Title (centered)
    ax.text(5, 9.2, "调研样本概览",
            ha="center", va="center",
            fontsize=11, fontweight="bold", color=TEXT_DARK)
    ax.text(5, 8.3, "数据来源：小红书“澳门旅游攻略”关键词，覆盖 2023–2025 年",
            ha="center", va="center",
            fontsize=7.5, color=TEXT_MUTED)

    plt.tight_layout()
    save_both(fig, "fig01_research_overview", output_dir)
    plt.close()


def fig02_route_information_demand(output_dir):
    """Figure 2: Tourist Demand for Route & Guide Info."""
    apply_report_style()

    categories = ["攻略", "路线"]
    values = [FIG2_DATA[k] for k in categories]

    fig, ax = plt.subplots(figsize=(REPORT_WIDTH, 2.6))

    y_pos = np.arange(len(categories))
    colors = [ACCENT_BAR, PRIMARY_BAR]

    bars = ax.barh(y_pos, values, height=0.6, color=colors,
                   edgecolor="none", zorder=2)

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 3, bar.get_y() + bar.get_height() / 2,
                f"{val} 次",
                ha="left", va="center",
                fontsize=9, color=TEXT_DARK, fontweight="bold")

    # Y labels
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=9.5)

    # Light gridlines
    ax.xaxis.grid(True, linestyle="-", linewidth=0.5, color=GRID_COLOR, zorder=0)
    ax.set_axisbelow(True)

    ax.set_xlim(0, max(values) * 1.25)
    ax.set_xticks([])

    # Title (centered on figure)
    fig.suptitle("游客对攻略与路线信息的关注度", fontsize=11, fontweight="bold",
                 color=TEXT_DARK, y=0.97)
    ax.text(0.5, -0.22, "高赞笔记标题与正文中核心需求关键词出现频次",
            transform=ax.transAxes,
            fontsize=7.5, color=TEXT_MUTED, ha="center")

    plt.tight_layout()
    save_both(fig, "fig02_route_information_demand", output_dir)
    plt.close()


def fig03_user_pain_points(output_dir):
    """Figure 3: Main Pain Point Categories."""
    apply_report_style()

    # Sort descending
    sorted_items = sorted(FIG3_DATA.items(), key=lambda x: x[1], reverse=True)
    categories = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    fig, ax = plt.subplots(figsize=(REPORT_WIDTH, 4.2))

    y_pos = np.arange(len(categories))
    colors = [ACCENT_BAR] + [PRIMARY_BAR] * (len(categories) - 1)

    bars = ax.barh(y_pos, values, height=0.65, color=colors,
                   edgecolor="none", zorder=2)

    # Value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height() / 2,
                f"{val} 次",
                ha="left", va="center",
                fontsize=9, color=TEXT_DARK, fontweight="bold")

    # Y labels
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=9.5)

    # Light gridlines
    ax.xaxis.grid(True, linestyle="-", linewidth=0.5, color=GRID_COLOR, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks([])

    ax.set_xlim(0, max(values) * 1.22)

    # Title (centered on figure)
    fig.suptitle("游客主要痛点类型分布", fontsize=11, fontweight="bold",
                 color=TEXT_DARK, y=0.97)

    # Keyword annotations below — vertical layout
    annotation_lines = [
        "关键词示例：",
        "信息获取困惑：怎么 / 去哪 / 不会 / 不知道 / 不懂",
        "路线与体力负担：步行 / 累 / 回头路 / 暴走",
        "文化理解需求：历史 / 文化 / 为什么 / 介绍 / 背景 / 故事",
        "人流拥挤压力：排队 / 人多 / 拥挤 / 爆满",
    ]
    for i, line in enumerate(annotation_lines):
        weight = "bold" if i == 0 else "normal"
        ax.text(0, -0.10 - i * 0.055, line,
                transform=ax.transAxes,
                fontsize=7.2, color=TEXT_MUTED, ha="left",
                fontweight=weight)

    plt.tight_layout()
    save_both(fig, "fig03_user_pain_points", output_dir)
    plt.close()


def fig04_physical_route_burden(output_dir):
    """Figure 4: Physical & Route Burden Breakdown."""
    apply_report_style()

    sorted_items = sorted(FIG4_DATA.items(), key=lambda x: x[1], reverse=True)
    categories = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    fig, ax = plt.subplots(figsize=(REPORT_WIDTH, 2.6))

    y_pos = np.arange(len(categories))
    colors = [ACCENT_BAR] + [PRIMARY_BAR] * (len(categories) - 1)

    bars = ax.barh(y_pos, values, height=0.6, color=colors,
                   edgecolor="none", zorder=2)

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{val} 次",
                ha="left", va="center",
                fontsize=9, color=TEXT_DARK, fontweight="bold")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=9.5)

    ax.xaxis.grid(True, linestyle="-", linewidth=0.5, color=GRID_COLOR, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks([])

    ax.set_xlim(0, max(values) * 1.22)

    # Title (centered on figure)
    fig.suptitle("路线与体力负担相关表达细分", fontsize=11, fontweight="bold",
                 color=TEXT_DARK, y=0.97)
    ax.text(0.5, -0.22, "游客对步行强度及路线安排的相关反馈",
            transform=ax.transAxes,
            fontsize=7.5, color=TEXT_MUTED, ha="center")

    plt.tight_layout()
    save_both(fig, "fig04_physical_route_burden", output_dir)
    plt.close()


def fig05_cultural_understanding_need(output_dir):
    """Figure 5: Cultural Understanding Demand Breakdown."""
    apply_report_style()

    sorted_items = sorted(FIG5_DATA.items(), key=lambda x: x[1], reverse=True)
    categories = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    fig, ax = plt.subplots(figsize=(REPORT_WIDTH, 3.4))

    y_pos = np.arange(len(categories))
    colors = [ACCENT_BAR] + [PRIMARY_BAR] * (len(categories) - 1)

    bars = ax.barh(y_pos, values, height=0.55, color=colors,
                   edgecolor="none", zorder=2)

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val} 次",
                ha="left", va="center",
                fontsize=9, color=TEXT_DARK, fontweight="bold")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=9.5)

    ax.xaxis.grid(True, linestyle="-", linewidth=0.5, color=GRID_COLOR, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks([])

    ax.set_xlim(0, max(values) * 1.18)

    # Title (centered on figure)
    fig.suptitle("游客文化理解需求相关表达细分", fontsize=11, fontweight="bold",
                 color=TEXT_DARK, y=0.97)
    ax.text(0.5, -0.16, "评论样本中与历史文化讲解需求相关的表达频次",
            transform=ax.transAxes,
            fontsize=7.5, color=TEXT_MUTED, ha="center")

    plt.tight_layout()
    save_both(fig, "fig05_cultural_understanding_need", output_dir)
    plt.close()


# =============================================================================
# MAIN
# =============================================================================

def main():
    base_dir = Path(__file__).resolve().parent.parent
    output_dir = base_dir / "figures"

    print("=" * 60)
    print("Generating Report Figures")
    print(f"Output: {output_dir}")
    print(f"Chinese font detected: {detect_chinese_font()}")
    print("=" * 60)

    fig01_research_overview(output_dir)
    fig02_route_information_demand(output_dir)
    fig03_user_pain_points(output_dir)
    fig04_physical_route_burden(output_dir)
    fig05_cultural_understanding_need(output_dir)

    print("\nAll figures generated successfully.")


if __name__ == "__main__":
    main()
