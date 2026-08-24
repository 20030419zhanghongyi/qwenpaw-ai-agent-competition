/**
 * MapLayerScene — Act II "Two Maps" visual event.
 *
 * Two abstract cartographic layers appear with a permanent offset,
 * creating the sense that two maps describe the same city but cannot
 * perfectly align — because what's missing is not a location, but time.
 *
 * Visual stages (tap / Enter / Space to advance):
 *   0. map1_appear  — first map fades in
 *   1. map1_text    — "一张图，记录道路、坐标与边界。"
 *   2. map2_appear  — second map overlays with offset
 *   3. map2_text    — "另一张图，记录山海、庙宇与人的名字。"
 *   4. offset_show  — offset becomes visible, both maps dim slightly
 *   5. reveal       — "缺失的不是地点。"
 *   6. emphasis     — "是时间。" (large, high emphasis)
 *   7. done         — fires onComplete
 *
 * All decorative layers use pointer-events-none.
 * Click on the container advances stages.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useStoryMessages } from "@/features/story/storyI18n";

export interface MapLayerSceneProps {
  leftLabel: string;
  rightLabel: string;
  revealText: string;
  /** Fired when all map stages have completed and user taps. */
  onComplete: () => void;
  /** Custom hint shown between stages. */
  hint?: string;
}

type MapStage =
  | "map1_appear"
  | "map1_text"
  | "map2_appear"
  | "map2_text"
  | "fade"
  | "reveal"
  | "done";

const STAGES: MapStage[] = [
  "map1_appear",
  "map1_text",
  "map2_appear",
  "map2_text",
  "fade",
  "reveal",
  "done",
];

const STAGE_DELAYS: Partial<Record<MapStage, number>> = {
  map1_appear: 800,
  map2_appear: 800,
  fade: 1000,
};

export function MapLayerScene({
  leftLabel,
  rightLabel,
  revealText,
  onComplete,
  hint,
}: MapLayerSceneProps) {
  const st = useStoryMessages();
  const [stageIndex, setStageIndex] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const hasCompleted = useRef(false); // guard against double-onComplete

  const stage = STAGES[stageIndex] ?? "done";

  // ── Reduced motion ────────────────────────────────────────────────────
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  // ── Auto-advance through timed stages ─────────────────────────────────
  useEffect(() => {
    const delay = STAGE_DELAYS[stage];
    if (!delay || reducedMotion) return;
    const timer = setTimeout(() => advance(), delay);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, reducedMotion]);

  // ── Advance ───────────────────────────────────────────────────────────
  const advance = useCallback(() => {
    if (hasCompleted.current) return; // block all input after completion
    setStageIndex((prev) => {
      const next = Math.min(prev + 1, STAGES.length - 1);
      if (STAGES[next] === "done") {
        if (hasCompleted.current) return next; // already firing
        hasCompleted.current = true;
        setTimeout(() => onComplete(), 400);
      }
      return next;
    });
  }, [onComplete]);

  // ── Interaction ───────────────────────────────────────────────────────
  const handleClick = useCallback(() => {
    advance();
  }, [advance]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        advance();
      }
    },
    [advance],
  );

  useEffect(() => {
    containerRef.current?.focus();
  }, []);

  // ── Visibility helpers ────────────────────────────────────────────────
  const stageAtLeast = (s: MapStage) => STAGES.indexOf(stage) >= STAGES.indexOf(s);
  // Reserved for future per-stage animation tuning

  return (
    <div
      ref={containerRef}
      role="region"
      aria-label={st("mapPerformance")}
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className="relative flex flex-1 flex-col items-center justify-center overflow-hidden outline-none select-none"
    >
      {/* ── Map layer 1 — warm ochre cartographic grid ────────────────── */}
      <div
        className="pointer-events-none absolute inset-[12%] rounded-sm"
        style={{
          opacity: stageAtLeast("map1_appear") ? 1 : 0,
          transform: `rotate(-1.8deg) translateX(${stageAtLeast("map2_appear") ? "-18px" : "0px"})`,
          transition: reducedMotion ? "none" : "opacity 1200ms ease, transform 1000ms ease",
        }}
      >
        {/* Grid */}
        <div
          className="absolute inset-0 rounded-sm border border-ochre/25"
          style={{
            backgroundImage: `
              linear-gradient(rgba(200,170,130,0.12) 1px, transparent 1px),
              linear-gradient(90deg, rgba(200,170,130,0.12) 1px, transparent 1px)
            `,
            backgroundSize: "48px 48px",
          }}
        />
        {/* Subtle contour lines */}
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 400 300" preserveAspectRatio="none">
          <path
            d="M20,150 Q100,80 180,160 T380,120"
            fill="none"
            stroke="rgba(200,170,130,0.22)"
            strokeWidth="1"
          />
          <path
            d="M10,180 Q120,130 200,190 T390,160"
            fill="none"
            stroke="rgba(200,170,130,0.15)"
            strokeWidth="0.8"
          />
          <path
            d="M30,200 Q80,170 160,210 T370,190"
            fill="none"
            stroke="rgba(200,170,130,0.12)"
            strokeWidth="0.6"
          />
        </svg>
      </div>

      {/* ── Map layer 2 — muted sage cartographic grid, offset ────────── */}
      <div
        className="pointer-events-none absolute inset-[12%] rounded-sm"
        style={{
          opacity: stageAtLeast("map2_appear") ? 1 : 0,
          transform: `rotate(1.2deg) translateX(${stageAtLeast("map2_appear") ? "18px" : "0px"}) translateY(-6px)`,
          transition: reducedMotion ? "none" : "opacity 1200ms ease, transform 1000ms ease",
        }}
      >
        <div
          className="absolute inset-0 rounded-sm border border-sage/20"
          style={{
            backgroundImage: `
              linear-gradient(rgba(150,175,155,0.10) 1px, transparent 1px),
              linear-gradient(90deg, rgba(150,175,155,0.10) 1px, transparent 1px)
            `,
            backgroundSize: "56px 56px",
          }}
        />
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 400 300" preserveAspectRatio="none">
          <path
            d="M50,100 Q150,50 250,110 T370,80"
            fill="none"
            stroke="rgba(150,175,155,0.18)"
            strokeWidth="1"
          />
          <path
            d="M40,140 Q140,110 260,160 T380,130"
            fill="none"
            stroke="rgba(150,175,155,0.12)"
            strokeWidth="0.8"
          />
        </svg>
      </div>

      {/* ── Text overlay ────────────────────────────────────────────────── */}
      <div className="relative z-10 flex flex-col items-center px-6 text-center">
        {/* Map 1 label — dims after fade stage */}
        <p
          className={`font-serif text-base leading-relaxed tracking-[0.03em] transition-all duration-1000 sm:text-lg ${
            stageAtLeast("fade")
              ? "translate-y-0 text-paper/25"
              : stageAtLeast("map1_text")
                ? "translate-y-0 text-paper/70"
                : "translate-y-4 text-paper/0"
          }`}
        >
          {leftLabel}
        </p>

        {/* Map 2 label — dims after fade stage */}
        <p
          className={`mt-6 font-serif text-base leading-relaxed tracking-[0.03em] transition-all duration-1000 sm:text-lg ${
            stageAtLeast("fade")
              ? "translate-y-0 text-paper/25"
              : stageAtLeast("map2_text")
                ? "translate-y-0 text-paper/70"
                : "translate-y-4 text-paper/0"
          }`}
        >
          {rightLabel}
        </p>

        {/* Reveal text — appears after fade */}
        <p
          className={`mt-10 font-serif text-lg leading-relaxed tracking-[0.04em] text-paper/85 transition-all duration-[1200ms] sm:text-xl ${
            stageAtLeast("reveal") ? "translate-y-0 opacity-100" : "translate-y-4 opacity-0"
          }`}
        >
          {revealText}
        </p>
      </div>

      {/* ── Hint ────────────────────────────────────────────────────────── */}
      {stage !== "done" && hint && (
        <div className="absolute bottom-16 left-0 right-0 z-10 text-center">
          <p className="text-[11px] tracking-[0.22em] text-paper/20 animate-pulse" aria-hidden>
            {hint}
          </p>
        </div>
      )}

      {/* ── Done hint ───────────────────────────────────────────────────── */}
      {stage === "done" && (
        <div className="absolute bottom-16 left-0 right-0 z-10 text-center">
          <p className="text-[11px] tracking-[0.22em] text-paper/20 animate-pulse" aria-hidden>
            ⌄
          </p>
        </div>
      )}
    </div>
  );
}
