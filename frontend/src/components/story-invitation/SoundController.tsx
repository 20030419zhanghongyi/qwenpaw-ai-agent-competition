/**
 * SoundController — minimal mute toggle for the cutscene overlay.
 *
 * Renders a tiny speaker icon in the top-right area (alongside Skip).
 * Visual direction: archival / restrained — not a bright UI control.
 */

import type { SoundAPI } from "./useSound";
import { useStoryMessages } from "@/features/story/storyI18n";

export interface SoundControllerProps {
  sound: SoundAPI;
}

export function SoundController({ sound }: SoundControllerProps) {
  const st = useStoryMessages();
  const soundLabel = sound.muted ? st("soundMuted") : st("soundPlaying");
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        sound.toggleMute();
      }}
      className="rounded-full px-3 py-1.5 text-[11px] tracking-[0.18em] text-paper/20 transition hover:text-paper/45 focus:outline-none focus:ring-1 focus:ring-ochre/40"
      aria-label={sound.muted ? st("soundOn") : st("soundOff")}
      title={soundLabel}
    >
      {soundLabel}
    </button>
  );
}
