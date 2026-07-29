import type { ReactNode } from "react";

interface PuzzleFrameProps {
  prompt: string;
  children: ReactNode;
  selectionHint?: string;
  canSubmit: boolean;
  disabled?: boolean;
  onSubmit: () => void;
}

export function PuzzleFrame({
  prompt,
  children,
  selectionHint,
  canSubmit,
  disabled = false,
  onSubmit,
}: PuzzleFrameProps) {
  return (
    <section className="space-y-4" aria-labelledby="story-puzzle-prompt">
      <div className="rounded-2xl border border-line bg-card p-4 shadow-[var(--shadow-soft)]">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-sage-deep">
          谜题
        </p>
        <h3
          id="story-puzzle-prompt"
          className="mt-2 font-sans text-base font-medium leading-7 text-ink"
        >
          {prompt}
        </h3>
        {selectionHint && (
          <p className="mt-1 text-[13px] leading-relaxed text-ink-soft">
            {selectionHint}
          </p>
        )}
        <div className="mt-4">{children}</div>
      </div>
      <button
        type="button"
        disabled={disabled || !canSubmit}
        onClick={onSubmit}
        className="min-h-12 w-full rounded-full bg-sage-deep px-5 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40"
      >
        {disabled ? "提交中…" : "提交答案"}
      </button>
    </section>
  );
}
