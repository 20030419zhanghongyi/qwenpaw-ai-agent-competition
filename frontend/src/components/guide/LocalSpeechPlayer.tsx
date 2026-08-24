import { useEffect, useMemo, useState } from "react";

import { t } from "@/i18n";
import type { LanguageCode } from "@/types";

type PlaybackState = "idle" | "speaking" | "paused";

const SPEECH_LANGUAGE: Record<LanguageCode, string> = {
  "zh-CN": "zh-CN",
  "zh-TW": "zh-TW",
  en: "en-US",
  pt: "pt-PT",
};

const VOICE_PREFERENCES: Record<LanguageCode, string[]> = {
  "zh-CN": ["zh-CN"],
  "zh-TW": ["zh-TW"],
  en: ["en-US", "en-GB", "en"],
  pt: ["pt-PT", "pt-BR", "pt"],
};

const NATURAL_VOICE_NAMES: Record<LanguageCode, string[]> = {
  "zh-CN": ["sandy", "shelley", "reed", "tingting", "ting-ting"],
  "zh-TW": ["sandy", "shelley", "reed", "mei-jia", "meijia"],
  en: ["flo", "sandy", "shelley", "reed", "samantha", "ava", "daniel"],
  pt: ["joana", "catarina", "luciana", "felipe"],
};

function pickVoice(voices: SpeechSynthesisVoice[], language: LanguageCode) {
  const localVoices = voices.filter((voice) => voice.localService);
  const scored = localVoices
    .map((voice) => {
      const lang = voice.lang.toLowerCase();
      const name = voice.name.toLowerCase();
      let score = 0;

      VOICE_PREFERENCES[language].forEach((preferred, index) => {
        const normalized = preferred.toLowerCase();
        if (lang === normalized) score = Math.max(score, 500 - index * 35);
      });

      NATURAL_VOICE_NAMES[language].forEach((preferredName, index) => {
        if (name.includes(preferredName)) score += 220 - index * 20;
      });
      if (/enhanced|premium|natural|neural/.test(name)) score += 300;
      if (voice.default) score += 15;
      return { voice, score };
    })
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score);

  return scored[0]?.voice ?? null;
}

export function LocalSpeechPlayer({
  text,
  language,
}: {
  text: string;
  language: LanguageCode;
}) {
  const [playback, setPlayback] = useState<PlaybackState>("idle");
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [voiceUnavailable, setVoiceUnavailable] = useState(false);
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;

  useEffect(() => {
    if (!supported) return;
    const loadVoices = () => setVoices(window.speechSynthesis.getVoices());
    loadVoices();
    window.speechSynthesis.addEventListener("voiceschanged", loadVoices);
    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", loadVoices);
      window.speechSynthesis.cancel();
    };
  }, [supported, text, language]);

  const voice = useMemo(() => pickVoice(voices, language), [voices, language]);

  useEffect(() => {
    if (voice) setVoiceUnavailable(false);
  }, [voice]);

  function togglePlayback() {
    if (!supported || !text.trim()) return;
    if (playback === "speaking") {
      window.speechSynthesis.pause();
      setPlayback("paused");
      return;
    }
    if (playback === "paused") {
      window.speechSynthesis.resume();
      setPlayback("speaking");
      return;
    }

    if (!voice) {
      setVoiceUnavailable(true);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = SPEECH_LANGUAGE[language];
    utterance.rate = language === "zh-CN" || language === "zh-TW" ? 0.96 : 0.94;
    utterance.pitch = 0.98;
    utterance.voice = voice;
    utterance.onend = () => setPlayback("idle");
    utterance.onerror = () => setPlayback("idle");
    window.speechSynthesis.speak(utterance);
    setPlayback("speaking");
  }

  function stopPlayback() {
    if (!supported) return;
    window.speechSynthesis.cancel();
    setPlayback("idle");
  }

  if (!supported) {
    return <p className="mt-3 text-xs text-ink-soft">{t(language, "ttsUnavailable")}</p>;
  }

  const primaryLabel =
    playback === "speaking"
      ? t(language, "localTtsPause")
      : playback === "paused"
        ? t(language, "localTtsResume")
        : t(language, "localTtsPlay");

  return (
    <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line/70 pt-4">
      <button
        type="button"
        onClick={togglePlayback}
        className="inline-flex min-h-10 min-w-32 items-center justify-center gap-2 rounded-full bg-sage-deep px-4 text-sm text-paper transition hover:bg-sage-deep/90"
      >
        <span aria-hidden>{playback === "speaking" ? "Ⅱ" : "▶"}</span>
        <span>{primaryLabel}</span>
      </button>
      {playback !== "idle" ? (
        <button
          type="button"
          onClick={stopPlayback}
          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-full border border-line px-4 text-sm text-ink transition hover:bg-paper-warm"
        >
          <span aria-hidden>■</span>
          <span>{t(language, "localTtsStop")}</span>
        </button>
      ) : null}
      <p className={`w-full text-[11px] sm:w-auto ${voiceUnavailable ? "text-clay" : "text-ink-soft"}`}>
        {voiceUnavailable
          ? t(language, "localTtsVoiceMissing")
          : voice
            ? t(language, "localTtsDeviceVoice").replace("{voice}", voice.name)
            : t(language, "localTtsDeviceNote")}
      </p>
    </div>
  );
}
