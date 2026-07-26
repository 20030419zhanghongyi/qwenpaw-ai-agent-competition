/**
 * Authored cutscene content for 《莲城双图：消失的界线》
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
 *   Act III — Telegram: a letter from "澜" (Alan)
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

  // ── Act III: Telegram from 阿澜 ──────────────────────────────────────
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
      "见字如面。",
      "",
      "如果你正在阅读这封信，",
      "说明两张地图又一次找到了",
      "能够同时看见它们的人。",
      "",
      "不要急着判断",
      "哪一张是真的。",
      "",
      "因为——",
      "",
      "两张都真。",
      "两张都不完整。",
      "",
      "澳门留下的，不只有街道。",
      "",
      "还有一些，",
      "被时间移走的界线。",
      "",
      "如果你愿意，",
      "替我把它们找回来。",
      "",
      "—— 阿澜",
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
      preamble: "这封信，在等待你的回答。",
      question: "你愿意成为寻图人吗？",
      acceptLabel: "接受阿澜的邀请",
      declineLabel: "暂时不接受",
    },
  },
];
