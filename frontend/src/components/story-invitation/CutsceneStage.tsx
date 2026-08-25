/**
 * CutsceneStage — full-screen cutscene that plays through authored scenes.
 *
 * v2: Supports multiple scene renderers (typewriter, maps, telegram, decision)
 *     dispatched via the scene's `renderer` field. Decision is part of the
 *     cutscene — not a separate modal phase — so PreferencePage never re-appears.
 *
 * Visual direction: historical archive × mysterious letter × time exploration.
 *
 * Responsibilities:
 *  - Iterate through sceneIndex 0 → N-1.
 *  - Route to the correct scene renderer component.
 *  - Render per-scene background + decorations.
 *  - Provide Skip control + Sound toggle + Scene dots.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { TypewriterText } from "./TypewriterText";
import { MapLayerScene } from "./MapLayerScene";
import { SceneBackground } from "./SceneBackground";
import type { CutsceneScene } from "./scenes/lotusTelegram";
import type { SoundAPI } from "./useSound";
import { useStoryMessages } from "@/features/story/storyI18n";

export interface CutsceneStageProps {
  scenes: CutsceneScene[];
  /** Fired when all non-decision scenes have completed → enters decision. */
  onAllScenesComplete: () => void;
  /** Fired when the user clicks Skip. */
  onSkip: () => void;
  /** Fired when the user clicks Accept on the decision scene. */
  onAccept: () => void;
  /** Fired when the user clicks Decline on the decision scene. */
  onDecline: () => void;
  /** Sound API for audio cues. */
  sound: SoundAPI;
  /** Muted state for conditional rendering. */
  muted: boolean;
}

export function CutsceneStage({
  scenes,
  onAllScenesComplete,
  onSkip,
  onAccept,
  onDecline,
  sound,
}: CutsceneStageProps) {
  const st = useStoryMessages();
  const [sceneIndex, setSceneIndex] = useState(0);
  const [fadeKey, setFadeKey] = useState(0);
  const advancingRef = useRef(false);

  const scene = scenes[sceneIndex];
  const isLastScene = sceneIndex >= scenes.length - 1;
  const lastSceneIsDecision = scenes[scenes.length - 1]?.renderer === "decision";

  const goNext = useCallback(() => {
    if (advancingRef.current) return; // guard against double-advance
    advancingRef.current = true;
    if (isLastScene) {
      onAllScenesComplete();
    } else {
      setFadeKey((k) => k + 1);
      setSceneIndex((i) => i + 1);
    }
  }, [isLastScene, onAllScenesComplete]);

  // Reset advancing guard when sceneIndex changes
  useEffect(() => {
    advancingRef.current = false;
  }, [sceneIndex]);

  // Skip: jump to decision scene if it's the last scene, otherwise fire onSkip
  const handleSkip = useCallback(() => {
    if (lastSceneIsDecision && !isLastScene) {
      setFadeKey((k) => k + 1);
      setSceneIndex(scenes.length - 1);
    } else {
      onSkip();
    }
  }, [lastSceneIsDecision, isLastScene, scenes.length, onSkip]);

  // ── Scene transition: play audio cue when scene changes ─────────────
  useEffect(() => {
    const cue = scene?.audioCue;
    if (cue) sound.playCue(cue);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sceneIndex]);

  // ── Telegram tick callback ──────────────────────────────────────────
  const handleCharTyped = useCallback(() => {
    if (scene?.audioCue === "telegram_tick") {
      sound.playCue("telegram_tick");
    }
  }, [scene?.audioCue, sound]);

  // ── Scene completion ────────────────────────────────────────────────
  const handleSceneComplete = useCallback(() => {
    goNext();
  }, [goNext]);

  // ── Scene action (action button in typewriter scenes) ───────────────
  const handleSceneAction = useCallback(() => {
    goNext();
  }, [goNext]);

  if (!scene) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col bg-[#0e0d0c]"
      role="dialog"
      aria-modal="true"
      aria-label={st("storyPerformance")}
    >
      {/* ── Background layer ─────────────────────────────────────────── */}
      <SceneBackground background={scene.background} />

      {/* ── Subtle top vignette ──────────────────────────────────────── */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 z-[5] h-24 bg-gradient-to-b from-[#0d0d0d] to-transparent"
        aria-hidden
      />

      {/* ── Top bar: scene dots (left), sound + skip (right) ──────────── */}
      <div className="absolute top-2 left-4 z-20 flex gap-2" aria-hidden>
        {scenes.map((_, i) => (
          <span
            key={i}
            className={`block size-1.5 rounded-full transition-all duration-700 ${
              i === sceneIndex
                ? "w-4 bg-ochre/60"
                : i < sceneIndex
                  ? "bg-ochre/25"
                  : "bg-paper/8"
            }`}
          />
        ))}
      </div>

      <div className="absolute top-0 right-0 z-20 flex items-center gap-1 p-4">
        {/* Sound toggle */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            sound.toggleMute();
          }}
          className="rounded-full px-2 py-1.5 text-[11px] tracking-[0.18em] text-paper/20 transition hover:text-paper/45 focus:outline-none focus:ring-1 focus:ring-ochre/40"
          aria-label={sound.muted ? st("soundOn") : st("soundOff")}
        >
          {sound.muted ? st("soundMuted") : st("soundPlaying")}
        </button>

        {/* Skip */}
        <button
          type="button"
          onClick={handleSkip}
          className="rounded-full px-3 py-1.5 text-[11px] tracking-[0.18em] text-paper/20 transition hover:text-paper/45 focus:outline-none focus:ring-1 focus:ring-ochre/40"
        >
          {st("skipPerformance")}
        </button>
      </div>

      {/* ── Scene content (dispatched by renderer) ────────────────────── */}
      <div
        key={fadeKey}
        className="relative z-10 flex flex-1 flex-col animate-[fadeIn_800ms_ease]"
      >
        <SceneRenderer
          scene={scene}
          onComplete={handleSceneComplete}
          onAction={handleSceneAction}
          onAccept={onAccept}
          onDecline={onDecline}
          onCharTyped={handleCharTyped}
        />
      </div>
    </div>
  );
}

// ── Scene Renderer Dispatcher ─────────────────────────────────────────

interface SceneRendererProps {
  scene: CutsceneScene;
  onComplete: () => void;
  onAction: () => void;
  onAccept: () => void;
  onDecline: () => void;
  onCharTyped: () => void;
}

function SceneRenderer({
  scene,
  onComplete,
  onAction,
  onAccept,
  onDecline,
  onCharTyped,
}: SceneRendererProps) {
  switch (scene.renderer) {
    // ── Typewriter (Act I, Act III) ──────────────────────────────────
    case "typewriter":
      return (
        <TypewriterText
          key={scene.id}
          paragraphs={scene.paragraphs ?? []}
          actionLabel={scene.actionLabel}
          hint={scene.hint}
          keepAllParagraphs={scene.keepAllParagraphs}
          onAllComplete={onComplete}
          onAction={onAction}
          onCharTyped={scene.audioCue === "telegram_tick" ? onCharTyped : undefined}
        />
      );

    // ── Maps (Act II) ────────────────────────────────────────────────
    case "maps":
      return (
        <MapLayerScene
          key={scene.id}
          leftLabel={scene.mapConfig?.leftLabel ?? ""}
          rightLabel={scene.mapConfig?.rightLabel ?? ""}
          revealText={scene.mapConfig?.revealText ?? ""}
          hint={scene.hint}
          onComplete={onComplete}
        />
      );

    // ── Telegram (Act III) — typewriter + archival metadata ──────────
    case "telegram":
      return (
        <div key={scene.id} className="relative flex flex-1 flex-col">
          {/* Archival metadata decorations */}
          <TelegramDecorations meta={scene.telegramMeta} />
          <TypewriterText
            paragraphs={scene.paragraphs ?? []}
            hint={scene.hint}
            keepAllParagraphs={scene.keepAllParagraphs}
            onAllComplete={onComplete}
            onCharTyped={scene.audioCue === "telegram_tick" ? onCharTyped : undefined}
          />
        </div>
      );

    // ── Decision (Act IV) — integrated into cutscene ─────────────────
    case "decision":
      return (
        <DecisionScene
          key={scene.id}
          config={scene.decisionConfig}
          onAccept={onAccept}
          onDecline={onDecline}
        />
      );

    default:
      return null;
  }
}

// ── Telegram Decorations ──────────────────────────────────────────────

function TelegramDecorations({
  meta,
}: {
  meta?: { archiveLabel?: string; signalId?: string };
}) {
  if (!meta) return null;
  return (
    <>
      {/* Top-left: archive label */}
      <div className="pointer-events-none absolute top-8 left-6 z-10">
        <p
          className="font-mono text-[10px] tracking-[0.25em] text-paper/15"
          style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace" }}
        >
          {meta.archiveLabel ?? ""}
        </p>
      </div>
      {/* Top-right: signal ID */}
      <div className="pointer-events-none absolute top-8 right-6 z-10">
        <p
          className="font-mono text-[10px] tracking-[0.25em] text-paper/15"
          style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace" }}
        >
          {meta.signalId ?? ""}
        </p>
      </div>
      {/* Subtle horizontal line near top */}
      <div
        className="pointer-events-none absolute top-16 left-6 right-6 z-10 border-t border-paper/5"
        aria-hidden
      />
    </>
  );
}

// ── Decision Scene (Act IV) ───────────────────────────────────────────
//
// Rendered INSIDE the cutscene, not as a separate modal. Uses the same
// dark background, so PreferencePage is never visible underneath.

function DecisionScene({
  config,
  onAccept,
  onDecline,
}: {
  config?: {
    preamble: string;
    question: string;
    acceptLabel: string;
    declineLabel: string;
  };
  onAccept: () => void;
  onDecline: () => void;
}) {
  const [showQuestion, setShowQuestion] = useState(false);
  const [loading, setLoading] = useState(false);

  // Preamble appears first, then question + buttons after a pause
  useEffect(() => {
    const timer = setTimeout(() => setShowQuestion(true), 1500);
    return () => clearTimeout(timer);
  }, []);

  if (!config) return null;

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6">
      {/* Preamble */}
      <p
        className={`font-serif text-lg leading-loose tracking-[0.04em] text-paper/70 transition-all duration-[1200ms] sm:text-xl ${
          showQuestion ? "translate-y-0 opacity-70" : "translate-y-2 opacity-100"
        }`}
      >
        {config.preamble}
      </p>

      {/* Question */}
      <p
        className={`mt-8 font-serif text-xl leading-loose tracking-[0.04em] text-paper/90 transition-all duration-[1200ms] sm:text-2xl ${
          showQuestion ? "translate-y-0 opacity-100" : "translate-y-6 opacity-0"
        }`}
      >
        {config.question}
      </p>

      {/* Buttons */}
      <div
        className={`mt-12 w-full max-w-[420px] space-y-3 transition-all duration-[1200ms] ${
          showQuestion ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"
        }`}
      >
        {/* Accept — warm muted gold, not bright yellow */}
        <button
          type="button"
          disabled={loading || !showQuestion}
          onClick={() => {
            setLoading(true);
            onAccept();
          }}
          className="w-full rounded-full border border-ochre/40 bg-ochre/15 px-6 py-4 text-base font-medium tracking-[0.04em] text-ochre transition hover:border-ochre/60 hover:bg-ochre/20 active:scale-[0.99] disabled:opacity-30"
        >
          {config.acceptLabel}
        </button>

        {/* Decline — text/outline only */}
        <button
          type="button"
          disabled={loading || !showQuestion}
          onClick={onDecline}
          className="w-full rounded-full border border-paper/10 px-6 py-4 text-base font-medium tracking-[0.04em] text-paper/30 transition hover:border-paper/25 hover:text-paper/50 active:scale-[0.99] disabled:opacity-20"
        >
          {config.declineLabel}
        </button>
      </div>
    </div>
  );
}
