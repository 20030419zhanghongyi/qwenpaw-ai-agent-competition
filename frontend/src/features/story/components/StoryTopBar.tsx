import type { ReactNode } from "react";
import { useStoryMessages } from "../storyI18n";
import { PetalProgress } from "./PetalProgress";

interface StoryTopBarProps {
  title: string;
  eyebrow?: string;
  onBack: () => void;
  backLabel?: string;
  petals?: number;
  totalPetals?: number;
  onAskAgent?: () => void;
  agentLabel?: string;
  trailing?: ReactNode;
}

export function StoryTopBar({
  title,
  eyebrow,
  onBack,
  backLabel,
  petals,
  totalPetals = 5,
  onAskAgent,
  agentLabel,
  trailing,
}: StoryTopBarProps) {
  const st = useStoryMessages();
  const resolvedBackLabel = backLabel ?? st("back");
  const resolvedAgentLabel = agentLabel ?? st("askAlian");
  return (
    <header
      className="sticky top-0 z-30 border-b border-line/80 bg-paper/95 px-4 pb-3 backdrop-blur-md"
      style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}
    >
      <div className="mx-auto grid max-w-[480px] grid-cols-[auto_1fr_auto] items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex min-h-11 min-w-11 items-center rounded-full px-2 text-sm text-ink-soft transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage"
          aria-label={resolvedBackLabel}
        >
          <span aria-hidden>←</span>
          <span className="sr-only">{resolvedBackLabel}</span>
        </button>
        <div className="min-w-0 text-center">
          {eyebrow && (
            <p className="truncate text-[11px] font-semibold uppercase tracking-[0.14em] text-ochre">
              {eyebrow}
            </p>
          )}
          <p className="truncate font-serif text-sm font-semibold text-ink">
            {title}
          </p>
          {petals != null && (
            <div className="mt-1 flex justify-center">
              <PetalProgress collected={petals} total={totalPetals} compact />
            </div>
          )}
        </div>
        <div className="flex min-w-11 justify-end">
          {onAskAgent ? (
            <button
              type="button"
              onClick={onAskAgent}
              className="min-h-11 rounded-full border border-sage-deep/25 bg-sage-deep/5 px-3 text-xs font-medium text-sage-deep transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage"
            >
              {resolvedAgentLabel}
            </button>
          ) : (
            trailing ?? <span className="block min-w-11" aria-hidden />
          )}
        </div>
      </div>
    </header>
  );
}
