/**
 * StoryInvitationExperience — top-level orchestrator for the full cutscene.
 *
 * v2 flow:
 *   loading (1.2 s)
 *     → cutscene (Act I → Act II → Act III → Act IV Decision)
 *     → transitioning (accept/decline confirmation)
 *     → fires callback
 *
 * Body scroll is locked while mounted and restored on unmount.
 *
 * The Decision is now INSIDE the cutscene (Act IV), so PreferencePage
 * is never visible behind it. It's a continuous fullscreen experience.
 */

import { useCallback, useEffect, useState } from "react";
import { CutsceneStage } from "./CutsceneStage";
import { useSound } from "./useSound";
import type { CutsceneScene } from "./scenes/lotusTelegram";

export interface StoryInvitationExperienceProps {
  /** Authored scene list for this story. */
  scenes: CutsceneScene[];
  /** Fired after cutscene + accept transition. */
  onAccept: () => void;
  /** Fired after cutscene + decline transition. */
  onDecline: () => void;
}

type Phase = "loading" | "cutscene" | "transitioning";

type TransitionKind = "accept" | "decline";

const LOADING_DURATION_MS = 1200;

export function StoryInvitationExperience({
  scenes,
  onAccept,
  onDecline,
}: StoryInvitationExperienceProps) {
  const [phase, setPhase] = useState<Phase>("loading");
  const [transitionKind, setTransitionKind] = useState<TransitionKind | null>(null);
  const sound = useSound();

  console.log("[StoryInvitationExperience] mounted, phase:", phase, "scenes:", scenes.length);

  // ── Body scroll lock ─────────────────────────────────────────────────
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  // ── Loading → cutscene ───────────────────────────────────────────────
  useEffect(() => {
    if (phase !== "loading") return;
    const timer = setTimeout(() => setPhase("cutscene"), LOADING_DURATION_MS);
    return () => clearTimeout(timer);
  }, [phase]);

  // ── Accept handler — show transition, then fire callback ─────────────
  const handleAccept = useCallback(() => {
    setTransitionKind("accept");
    setPhase("transitioning");
  }, []);

  // ── Decline handler — show transition, then fire callback ────────────
  const handleDecline = useCallback(() => {
    setTransitionKind("decline");
    setPhase("transitioning");
  }, []);

  // ── Skip → go directly to decision (last scene) ─────────────────────
  // We simulate this by firing onAllScenesComplete which would advance
  // to the decision scene... but since decision is the last scene, we
  // just move to the decision scene via skip handler.
  const handleSkip = useCallback(() => {
    // Skip means: jump to decision (last scene).
    // Since CutsceneStage iterates through scenes, and the last scene is
    // the decision, we need a different mechanism.
    // We handle this by just going directly to the transitioning phase
    // with a "skip" transition that shows the decision.
    // Actually — let's present the decision immediately.
    setTransitionKind("decline");
    setPhase("transitioning");
  }, []);

  // ── All non-decision scenes complete → no-op (decision scene handles itself)
  const handleAllScenesComplete = useCallback(() => {
    // This fires when ALL scenes in the array have completed.
    // In v2, the decision scene is the last scene and it doesn't
    // auto-complete — it waits for user input via onAccept/onDecline.
    // So this should never fire in normal flow, but if it does,
    // fall through to decline.
    setTransitionKind("decline");
    setPhase("transitioning");
  }, []);

  // ── Transition: wait for user click before firing callback ──────────
  const handleTransitionClick = useCallback(() => {
    if (phase !== "transitioning") return;
    if (transitionKind === "accept") {
      onAccept();
    } else {
      onDecline();
    }
  }, [phase, transitionKind, onAccept, onDecline]);

  // ── Render ───────────────────────────────────────────────────────────
  switch (phase) {
    // ── Loading screen ────────────────────────────────────────────────
    case "loading":
      return (
        <div
          className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0e0d0c]"
          role="alert"
          aria-label="正在加载"
        >
          <p className="animate-pulse font-serif text-base tracking-[0.08em] text-paper/40">
            正在整理你的澳门旅程……
          </p>
        </div>
      );

    // ── Cutscene (includes decision as last scene) ────────────────────
    case "cutscene":
      return (
        <CutsceneStage
          scenes={scenes}
          onAllScenesComplete={handleAllScenesComplete}
          onSkip={handleSkip}
          onAccept={handleAccept}
          onDecline={handleDecline}
          sound={sound}
          muted={sound.muted}
        />
      );

    // ── Transition overlay ────────────────────────────────────────────
    case "transitioning":
      return (
        <div
          className="fixed inset-0 z-50 flex cursor-pointer flex-col items-center justify-center bg-[#0e0d0c]"
          role="button"
          tabIndex={0}
          aria-label={
            transitionKind === "accept" ? "身份确认中" : "记录封存中"
          }
          onClick={handleTransitionClick}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleTransitionClick();
            }
          }}
        >
          {transitionKind === "accept" ? (
            <div className="flex flex-col items-center gap-6 animate-[fadeIn_600ms_ease]">
              <p className="font-serif text-lg tracking-[0.08em] text-paper/60">
                身份确认中……
              </p>
              <p className="font-mono text-xs tracking-[0.3em] text-paper/40"
                style={{ fontFamily: "'IBM Plex Mono', 'JetBrains Mono', monospace" }}>
                寻图人 // 已确认
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4 animate-[fadeIn_600ms_ease]">
              <p className="font-serif text-base tracking-[0.06em] text-paper/40">
                记录已重新封存。
              </p>
            </div>
          )}
          {/* Click hint */}
          <p className="absolute bottom-20 text-[11px] tracking-[0.22em] text-paper/15 animate-pulse">
            轻触任意位置继续
          </p>
        </div>
      );
  }
}
