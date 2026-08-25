/**
 * TypewriterText — animated paragraph-by-paragraph text reveal.
 *
 * v2 changes:
 *  - Old paragraphs fade to ghost (15-25%) instead of accumulating at 70%.
 *    Only the current paragraph + the immediately preceding one are visible;
 *    earlier paragraphs are hidden entirely. This creates a film-subtitle /
 *    visual-novel feel rather than an article.
 *  - Custom `hint` prop per scene (undefined = no hint).
 *  - Optional `onCharTyped` callback for external sound throttling.
 *
 * Preserved interaction (unchanged from v1):
 *  - Tap / Enter / Space during typing → immediately reveal full paragraph.
 *  - Tap / Enter / Space after paragraph complete → advance to next.
 *  - After last paragraph with actionLabel → show action button, bg tap blocked.
 *  - After last paragraph without actionLabel → onAllComplete fires on tap.
 *  - Action button uses stopPropagation.
 *  - prefers-reduced-motion → disable animation, show full text.
 *  - Auto-scroll to keep current paragraph visible.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useStoryMessages } from "@/features/story/storyI18n";

export interface TypewriterTextProps {
  /** Paragraphs to reveal, one at a time. Empty string = visual break. */
  paragraphs: string[];
  /** Milliseconds per character (default 40). */
  speedMs?: number;
  /**
   * If set, an action button is shown after the last paragraph instead of
   * calling onAllComplete. Background tap MUST NOT bypass this button.
   */
  actionLabel?: string;
  /** Fired after the last paragraph is complete AND the user taps (no actionLabel). */
  onAllComplete?: () => void;
  /** Fired when the action button is clicked (only when actionLabel is set). */
  onAction?: () => void;
  /**
   * Custom bottom hint text. Shown when a paragraph is complete and waiting
   * for user to advance. Undefined → no hint shown.
   */
  hint?: string;
  /** Fired each time a character is typed. For external sound throttling. */
  onCharTyped?: () => void;
  /**
   * When true, ALL previously-typed paragraphs remain visible (progressively
   * faded by distance). Use for letter/telegram scenes where the full text
   * should accumulate on screen.
   */
  keepAllParagraphs?: boolean;
}

export function TypewriterText({
  paragraphs,
  speedMs = 40,
  actionLabel,
  onAllComplete,
  onAction,
  hint,
  onCharTyped,
  keepAllParagraphs = false,
}: TypewriterTextProps) {
  const st = useStoryMessages();
  const [paraIndex, setParaIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const currentRef = useRef<HTMLParagraphElement>(null);

  // ── Detect reduced-motion preference ──────────────────────────────────
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  // ── Reset when paragraphs change (fresh scene) ────────────────────────
  useEffect(() => {
    setParaIndex(0);
    setCharIndex(0);
  }, [paragraphs]);

  // ── Typing timer ──────────────────────────────────────────────────────
  const currentPara = paragraphs[paraIndex] ?? "";
  const isLastPara = paraIndex >= paragraphs.length - 1;
  const isComplete = charIndex >= currentPara.length;

  useEffect(() => {
    if (reducedMotion || currentPara.length === 0) {
      setCharIndex(currentPara.length);
      return;
    }
    if (isComplete) return;

    const timer = setTimeout(() => {
      setCharIndex((prev) => {
        const next = Math.min(prev + 1, currentPara.length);
        return next;
      });
      onCharTyped?.();
    }, speedMs);

    return () => clearTimeout(timer);
  }, [paraIndex, charIndex, currentPara, speedMs, reducedMotion, isComplete, onCharTyped]);

  // ── Auto-scroll to keep current paragraph visible ─────────────────────
  // When keepAllParagraphs: scroll only on paragraph change (not per-char),
  // so the user can read accumulating text without viewport churn, but new
  // paragraphs always scroll into view.
  useEffect(() => {
    if (keepAllParagraphs) return; // skip per-char scroll
    currentRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [charIndex, keepAllParagraphs]);

  useEffect(() => {
    currentRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [paraIndex]);

  // ── Advance logic ─────────────────────────────────────────────────────
  const advance = useCallback(() => {
    if (!isComplete) {
      setCharIndex(currentPara.length);
      return;
    }
    if (!isLastPara) {
      setParaIndex((prev) => prev + 1);
      setCharIndex(0);
      return;
    }
    // Last paragraph complete, no action label → notify parent.
    if (!actionLabel && onAllComplete) {
      onAllComplete();
    }
  }, [isComplete, isLastPara, currentPara.length, actionLabel, onAllComplete]);

  // ── Interaction handlers ──────────────────────────────────────────────
  const handleClick = useCallback(() => {
    advance();
  }, [advance]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        if (isLastPara && isComplete && actionLabel) return;
        advance();
      }
    },
    [advance, isLastPara, isComplete, actionLabel],
  );

  // ── Focus container on mount for keyboard ─────────────────────────────
  useEffect(() => {
    containerRef.current?.focus();
  }, []);

  // ── Compute display ───────────────────────────────────────────────────
  const displayText = reducedMotion ? currentPara : currentPara.slice(0, charIndex);
  const showCursor = !isComplete && !reducedMotion && currentPara.length > 0;
  const showAction = isLastPara && isComplete && !!actionLabel;
  const showHint = isComplete && !showAction && currentPara.length > 0 && hint !== undefined;

  // ── Opacity helper for faded paragraphs ───────────────────────────────
  // distance: how many paragraphs before the current one (1 = immediately preceding)
  const ghostOpacity = (distance: number): string => {
    if (distance <= 0) return ""; // current paragraph — use its own class
    if (keepAllParagraphs) {
      // All text stays on screen at full opacity — keep it readable
      return "";
    }
    // Default: only show current + immediate predecessor
    if (distance === 1) return "opacity-[0.22]";
    return "opacity-0"; // earlier paragraphs hidden entirely
  };

  return (
    <div
      ref={containerRef}
      role="region"
      aria-label={st("storyText")}
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className="flex flex-1 flex-col overflow-y-auto overscroll-contain px-6 pt-20 pb-16 outline-none select-none"
    >
      <div className={`mx-auto w-full max-w-[720px] ${keepAllParagraphs ? "space-y-1" : "space-y-4"}`}>
        {/* ── Completed paragraphs (faded ghosts) ────────────────────── */}
        {paragraphs.slice(0, paraIndex).map((para, i) => {
          const distance = paraIndex - i;
          if (!keepAllParagraphs && distance > 1) return null; // hide paragraphs older than 1
          if (para.length === 0) {
            return <div key={i} className={keepAllParagraphs ? "h-1" : "h-4"} aria-hidden />;
          }
          return (
            <p
              key={i}
              className={`font-serif text-lg tracking-[0.02em] text-paper/95 transition-opacity duration-1000 sm:text-xl ${ghostOpacity(distance)} ${keepAllParagraphs ? "leading-normal" : "leading-relaxed"}`}
            >
              {para}
            </p>
          );
        })}

        {/* ── Current paragraph (typing / just completed) ──────────── */}
        {currentPara.length === 0 ? (
          <div className={keepAllParagraphs ? "h-px" : "h-4"} aria-hidden />
        ) : (
          <p
            ref={currentRef}
            className={`font-serif text-lg tracking-[0.02em] text-paper/95 sm:text-xl ${keepAllParagraphs ? "leading-normal" : "leading-relaxed"}`}
          >
            {displayText}
            {showCursor && (
              <span
                className="ml-0.5 inline-block h-[1.1em] w-[0.15em] translate-y-[0.05em] bg-ochre/70 align-baseline animate-pulse"
                aria-hidden
              />
            )}
          </p>
        )}
      </div>

      {/* ── Tap hint ────────────────────────────────────────────────── */}
      {showHint && (
        <div
          className={`mx-auto w-full max-w-[720px] text-center ${
            keepAllParagraphs
              ? "sticky bottom-0 bg-gradient-to-t from-[#0e0d0c] via-[#0e0d0c]/95 to-transparent pb-4 pt-6"
              : "mt-10"
          }`}
        >
          <p className="text-[11px] tracking-[0.22em] text-paper/20 animate-pulse" aria-hidden>
            {hint || "⌄"}
          </p>
        </div>
      )}

      {/* ── Action button ──────────────────────────────────────────── */}
      {showAction && (
        <div className="mx-auto mt-10 w-full max-w-[720px] text-center">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onAction?.();
            }}
            className="inline-flex items-center gap-2 border-b border-ochre/40 px-2 py-1 text-base font-medium tracking-[0.15em] text-ochre/80 transition hover:border-ochre hover:text-ochre active:scale-[0.98]"
            autoFocus
          >
            {actionLabel}
          </button>
        </div>
      )}
    </div>
  );
}
