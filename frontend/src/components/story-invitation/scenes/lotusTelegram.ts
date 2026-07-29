/**
 * Authored invitation content for 《莲城双图：未尽之图》
 *
 * This file is PURE DATA — no React, no QwenPaw, no dynamic generation.
 * Keeping text deterministic ensures typewriter timing, visual transitions,
 * sound effects, and human CV can be synchronised later.
 *
 * Visual direction: historical archive × mysterious letter × time exploration.
 * The tone is "discovered records", not "system error".
 *
 * Scene structure (v2):
 *   Act I   — Interruption: an unarchived record surfaces during route generation
 *   Act II  — Two Maps: two map layers appear with permanent offset
 *   Act III — Telegram: the archived message reveals the research invitation
 *   Act IV  — Decision: the letter awaits an answer (integrated into cutscene)
 *
 * Audio cues (P0 — lightweight browser Audio):
 *   signal_appear  — subtle low click when unknown record appears
 *   telegram_tick  — VERY subtle telegraph tick, throttled per ~3 chars
 *   time_reveal    — low-frequency resonance for "是时间。" moment
 */

export type SceneRenderer = "typewriter" | "maps" | "telegram" | "decision";

export interface CutsceneScene {
  id: string;
  renderer: SceneRenderer;
  background: "dark" | "maps" | "telegram";
  /**
   * Custom bottom hint shown when a paragraph is complete.
   * Undefined → no hint. "" → fallback to default.
   */
  hint?: string;

  /* ── Typewriter renderer fields ── */
  paragraphs?: string[];
  actionLabel?: string;

  /* ── Maps renderer fields ── */
  mapConfig?: {
    leftLabel: string;
    rightLabel: string;
    offsetLabel: string;
    revealText: string;
    emphasisText: string;
  };

  /* ── Telegram renderer fields ── */
  telegramMeta?: {
    archiveLabel: string;
    signalId: string;
  };

  /* ── Decision renderer fields ── */
  decisionConfig?: {
    preamble: string;
    question: string;
    acceptLabel: string;
    declineLabel: string;
  };

  /**
   * Keep all previously-typed paragraphs visible (faded) instead of hiding
   * paragraphs older than the immediate predecessor. For letter/telegram scenes.
   */
  keepAllParagraphs?: boolean;

  /* ── Audio ── */
  audioCue?: "signal_appear" | "telegram_tick" | "time_reveal";
}

export const LOTUS_TELEGRAM_SCENES: CutsceneScene[] = [
  // ── Act I: Interruption ──────────────────────────────────────────────
  {
    id: "interruption",
    renderer: "typewriter",
    background: "dark",
    paragraphs: [
      "正在生成你的澳门路线……",
      "",
      "……",
      "",
      "发现未归档记录。",
      "来源：未知",
    ],
    actionLabel: "读取",
    audioCue: "signal_appear",
  },

  // ── Act II: The Two Maps ─────────────────────────────────────────────
  {
    id: "double_map",
    renderer: "maps",
    background: "maps",
    hint: "轻触查看下一层",
    mapConfig: {
      leftLabel: "一张地图，记录城市的街道。",
      rightLabel: "另一张地图，记录街道里的故事。",
      offsetLabel: "",
      revealText: "有些故事，地图上从来没有标出来。",
      emphasisText: "",
    },
    audioCue: "time_reveal",
  },

  // ── Act III: Story invitation ────────────────────────────────────────
  {
    id: "telegram",
    renderer: "telegram",
    background: "telegram",
    hint: "继续阅读",
    telegramMeta: {
      archiveLabel: "未归档记录",
      signalId: "SIGNAL 02",
    },
    paragraphs: [
      "寻图人：",
      "",
      "一本家藏旧书里，",
      "夹着两张绘法不同的澳门地图。",
      "",
      "一张记录城市的形状，",
      "一张记录人怎样在城市里生活。",
      "",
      "不要急着判断",
      "哪一张是真的。",
      "",
      "沿着五张秘密纸条，",
      "亲自走过六处真实地点，",
      "它们才会互相说明。",
      "",
      "这是一段约一天的城市漫游。",
      "五个谜题均可跳过。",
      "",
      "地图不是最后的判决。",
      "一座城市，由许多人共同写成。",
    ],
    keepAllParagraphs: true,
    audioCue: "telegram_tick",
  },

  // ── Act IV: Decision ─────────────────────────────────────────────────
  {
    id: "decision",
    renderer: "decision",
    background: "dark",
    decisionConfig: {
      preamble: "限定故事游 · 一日六站",
      question: "跟着两张旧地图，重新认识澳门？",
      acceptLabel: "进入《莲城双图》",
      declineLabel: "继续普通路线规划",
    },
  },
];
