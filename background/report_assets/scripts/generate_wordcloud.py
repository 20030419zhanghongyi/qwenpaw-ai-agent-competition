#!/usr/bin/env python3
"""
Generate word cloud from Xiaohongshu crawled data.
Usage: python3 background/report_assets/scripts/generate_wordcloud.py
"""

import pandas as pd
import jieba
import jieba.posseg as pseg
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import re
import os

# ========== Configuration ==========
DATA_PATH = "background/raw_data/xhs/xhs_search_20260528_204244.xlsx"
OUTPUT_PATH = "background/report_assets/figures/wordcloud_xhs.png"
FREQ_CSV_PATH = "background/report_assets/wordcloud_xhs_top_words.csv"
STOPWORDS_PATH = "scripts/chinese_stopwords.txt"
FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"  # macOS Chinese font
MAX_WORDS = 200
WIDTH = 1600
HEIGHT = 900

# ========== Stopwords ==========
DEFAULT_STOPWORDS = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也",
    "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那",
    "可以", "还", "但", "我们", "让", "来", "为", "能", "而", "被", "从", "什么", "这里",
    "话题", "www", "com", "http", "https", "xiaohongshu", "explore", "xsec_token", "xsec_source",
    "pc_search", "sign", "sns", "avatar", "xhscdn", "nd_dft_wlteh_webp", "notes_pre_post",
    "png", "jpg", "jpeg", "gif", "mp4", "stream", "video", "image", "url", "null", "na", "nan",
    "p", "n", "g", "o", "i", "e", "a", "r", "s", "t", "l", "c", "u", "d", "m", "h", "k",
    "就是", "非常", "真的", "还是", "不过", "因为", "所以", "如果", "然后", "当时", "现在",
    "大家", "东西", "感觉", "时间", "地方", "时候", "一下", "今天", "下次", "记得", "喜欢",
    "这次", "第一次", "超级", "一直", "已经", "特别", "比较", "很多", "一起", "每个",
    "全程", "整体", "各种", "一路", "直接", "大概", "左右", "样子", "关于", "并且",
    "❗", "❗️", "✅", "➡️", "📌", "🧸", "\n", "\t", "", " ", "nbsp", "r", "n", "\\",
    "手机", "APP", "app", "笔记", "关注", "主页", "搜索", "点击", "图片", "视频", "收藏",
    "点赞", "评论", "分享", "粉丝", "用户", "账号", "博主", "煮啵", "博主", "po", "PO",
}


def load_stopwords(path):
    """Load stopwords from file if exists."""
    stopwords = DEFAULT_STOPWORDS.copy()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word:
                    stopwords.add(word)
    return stopwords


def clean_text(text):
    """Clean raw text: remove URLs, tags, special chars."""
    if pd.isna(text):
        return ""
    text = str(text)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove [xxx] tags (e.g. [吧唧R], [话题])
    text = re.sub(r"\[[^\]]*\]", "", text)
    # Remove emoji and special symbols, keep Chinese/English/numbers
    text = re.sub(r"[^一-龥a-zA-Z0-9\s]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_meaningful_words(text, stopwords):
    """Segment Chinese text and filter meaningful words."""
    words = []
    # Use jieba with POS tagging to keep nouns, verbs, adjectives
    for word, flag in pseg.cut(text):
        word = word.strip().lower()
        if not word or len(word) == 1 or word in stopwords:
            continue
        # Keep nouns (n), place names (ns), organization (nt), verbs (v), adjectives (a)
        if flag.startswith(("n", "v", "a")) or flag in ("ns", "nt", "nz", "vn", "an"):
            words.append(word)
    return words


def generate_wordcloud(df, output_path):
    """Generate word cloud from Xiaohongshu data."""
    stopwords = load_stopwords(STOPWORDS_PATH)

    # Combine text fields: title + description + tags
    all_text_parts = []
    for _, row in df.iterrows():
        parts = []
        for col in ["title", "desc", "tag_list"]:
            if col in df.columns:
                parts.append(clean_text(row.get(col, "")))
        all_text_parts.append(" ".join(parts))

    full_text = " ".join(all_text_parts)
    print(f"Combined text length: {len(full_text)} chars")

    # Segment and filter words
    words = extract_meaningful_words(full_text, stopwords)
    word_freq = Counter(words)

    print(f"Total words extracted: {len(words)}")
    print(f"Unique words: {len(word_freq)}")
    print("\nTop 30 words:")
    for word, count in word_freq.most_common(30):
        print(f"  {word}: {count}")

    # Generate word cloud
    wordcloud = WordCloud(
        font_path=FONT_PATH,
        width=WIDTH,
        height=HEIGHT,
        background_color="white",
        max_words=MAX_WORDS,
        relative_scaling=0.5,
        colormap="tab10",
        prefer_horizontal=0.9,
        min_font_size=10,
        max_font_size=200,
        random_state=42,
    ).generate_from_frequencies(word_freq)

    # Save figure
    plt.figure(figsize=(20, 11.25), dpi=100)
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close()
    print(f"\nWord cloud saved to: {output_path}")

    return word_freq


def main():
    # Load data
    df = pd.read_excel(DATA_PATH)
    print(f"Loaded {len(df)} records from {DATA_PATH}")

    # Ensure output directories exist
    for path in (OUTPUT_PATH, FREQ_CSV_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    # Generate word cloud
    word_freq = generate_wordcloud(df, OUTPUT_PATH)

    # Also save top words to CSV for reference
    pd.DataFrame(word_freq.most_common(), columns=["word", "count"]).to_csv(
        FREQ_CSV_PATH, index=False, encoding="utf-8-sig"
    )
    print(f"Top words CSV saved to: {FREQ_CSV_PATH}")


if __name__ == "__main__":
    main()
