/**
 * useSound — lightweight browser-native audio hook for cutscene sound cues.
 *
 * P0 design:
 *  - No external audio library.
 *  - Synthesises simple cues via Web Audio API (OscillatorNode + GainNode).
 *  - Falls back silently if Web Audio is unavailable or autoplay is blocked.
 *  - Global mute toggle persisted in module-level variable for the session.
 *
 * Cues:
 *   signal_appear — subtle low click / signal pulse
 *   telegram_tick — VERY soft tick, meant to be throttled externally (~per 3 chars)
 *   time_reveal   — low-frequency resonance, ~0.5 s
 */

import { useCallback, useEffect, useState } from "react";

// ── Module-level mute state (shared across all useSound instances) ───
let globalMuted = false;
const muteListeners = new Set<() => void>();

function setGlobalMuted(v: boolean) {
  globalMuted = v;
  muteListeners.forEach((fn) => fn());
}

// ── Lazy AudioContext (created on first user gesture) ────────────────
let _ctx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (_ctx) return _ctx;
  try {
    _ctx = new AudioContext();
    // If suspended (autoplay policy), try to resume on next user gesture
    if (_ctx.state === "suspended") {
      const resume = () => {
        _ctx?.resume().catch(() => {});
        document.removeEventListener("click", resume);
        document.removeEventListener("keydown", resume);
      };
      document.addEventListener("click", resume);
      document.addEventListener("keydown", resume);
    }
    return _ctx;
  } catch {
    return null;
  }
}

// ── Throttle for telegram ticks ──────────────────────────────────────
let lastTickTime = 0;
const TICK_THROTTLE_MS = 80; // min interval between ticks (~3 chars at 40ms/char)

// ── Cue synthesis ──────────────────────────────────────────────────────

function playSignalAppear() {
  const ctx = getCtx();
  if (!ctx || globalMuted) return;
  try {
    const now = ctx.currentTime;
    // Very short sine click at ~800 Hz, quick decay
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(800, now);
    osc.frequency.exponentialRampToValueAtTime(200, now + 0.12);
    gain.gain.setValueAtTime(0.06, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
    osc.connect(gain).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.15);
  } catch {
    // silently ignore
  }
}

function playTelegramTick() {
  const now = Date.now();
  if (now - lastTickTime < TICK_THROTTLE_MS) return;
  lastTickTime = now;

  const ctx = getCtx();
  if (!ctx || globalMuted) return;
  try {
    const now = ctx.currentTime;
    // Very soft, short tick — like a telegraph key
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(1200, now);
    gain.gain.setValueAtTime(0.03, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
    osc.connect(gain).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.04);
  } catch {
    // silently ignore
  }
}

function playTimeReveal() {
  const ctx = getCtx();
  if (!ctx || globalMuted) return;
  try {
    const now = ctx.currentTime;
    // Low-frequency resonance — sustained ~0.6 s
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(80, now);
    osc.frequency.linearRampToValueAtTime(55, now + 0.6);
    gain.gain.setValueAtTime(0.05, now);
    gain.gain.linearRampToValueAtTime(0.08, now + 0.3);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.7);
    osc.connect(gain).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + 0.7);
  } catch {
    // silently ignore
  }
}

const CUE_PLAYERS: Record<string, () => void> = {
  signal_appear: playSignalAppear,
  telegram_tick: playTelegramTick,
  time_reveal: playTimeReveal,
};

// ── Hook ────────────────────────────────────────────────────────────────

export interface SoundAPI {
  /** Whether sound is currently muted. */
  muted: boolean;
  /** Toggle mute on/off. */
  toggleMute: () => void;
  /** Play a named cue. No-op if muted or unavailable. */
  playCue: (cue: string) => void;
  /** Begin a throttled tick sequence for typewriter. Returns a stop function. */
  startTelegramTicks: (charsPerTick?: number) => () => void;
}

export function useSound(): SoundAPI {
  const [muted, setMuted] = useState(globalMuted);

  // Sync with global mute changes
  useEffect(() => {
    const listener = () => setMuted(globalMuted);
    muteListeners.add(listener);
    return () => {
      muteListeners.delete(listener);
    };
  }, []);

  const toggleMute = useCallback(() => {
    setGlobalMuted(!globalMuted);
  }, []);

  const playCue = useCallback((cue: string) => {
    const player = CUE_PLAYERS[cue];
    if (player) player();
  }, []);

  // Throttled telegram tick: fires every N characters
  const startTelegramTicks = useCallback(
    (_charsPerTick = 3) => {
      // Telegram ticks are now auto-throttled per playTelegramTick().
      // This hook is reserved for future per-scene throttle control.
      return () => {
        // cleanup — no-op for now
      };
    },
    [],
  );

  return { muted, toggleMute, playCue, startTelegramTicks };
}
