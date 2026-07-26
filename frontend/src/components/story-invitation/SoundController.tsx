/**
 * SoundController — minimal mute toggle for the cutscene overlay.
 *
 * Renders a tiny speaker icon in the top-right area (alongside Skip).
 * Visual direction: archival / restrained — not a bright UI control.
 */

import type { SoundAPI } from "./useSound";

export interface SoundControllerProps {
  sound: SoundAPI;
}

export function SoundController({ sound }: SoundControllerProps) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        sound.toggleMute();
      }}
      className="rounded-full px-3 py-1.5 text-[11px] tracking-[0.18em] text-paper/20 transition hover:text-paper/45 focus:outline-none focus:ring-1 focus:ring-ochre/40"
      aria-label={sound.muted ? "开启声音" : "关闭声音"}
      title={sound.muted ? "声音 ○" : "声音 ◉"}
    >
      {sound.muted ? "声音 ○" : "声音 ◉"}
    </button>
  );
}
