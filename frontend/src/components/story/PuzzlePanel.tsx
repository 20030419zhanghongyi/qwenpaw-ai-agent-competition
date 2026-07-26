import { useState } from "react";
import type { StoryPuzzle } from "@/types/stories";

interface PuzzlePanelProps {
  puzzle: StoryPuzzle;
  disabled: boolean;
  onSubmitAnswer: (answer: unknown) => void;
  onRequestHint: () => void;
  onSkip: () => void;
  attempts: number;
  lastHint?: string | null;
  lastMessage?: string | null;
}

export function PuzzlePanel({
  puzzle,
  disabled,
  onSubmitAnswer,
  onRequestHint,
  onSkip,
  attempts,
  lastHint,
  lastMessage,
}: PuzzlePanelProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const isSingleChoice = puzzle.type === "single_choice";
  const isWrong = lastMessage && !lastMessage.includes("正确") && attempts > 0;

  const handleSubmit = () => {
    if (isSingleChoice && selected) {
      onSubmitAnswer(selected);
    }
  };

  return (
    <div className="space-y-4">
      {/* Puzzle prompt */}
      <div className="rounded-2xl border border-line bg-card p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sage-deep">
          谜题
        </p>
        <p className="mt-2 text-sm leading-relaxed text-ink">{puzzle.prompt}</p>

        {/* Single choice options */}
        {isSingleChoice && puzzle.options && (
          <div className="mt-4 space-y-2.5">
            {puzzle.options.map((opt) => {
              const isSelected = selected === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => setSelected(opt.id)}
                  className={`w-full rounded-xl border px-4 py-3 text-left text-sm transition ${
                    isSelected
                      ? "border-sage-deep bg-sage-deep/10 text-sage-deep font-medium"
                      : "border-line bg-paper hover:border-sage"
                  } disabled:opacity-50`}
                >
                  {opt.text}
                </button>
              );
            })}
          </div>
        )}

        {/* Feedback */}
        {lastMessage && (
          <p
            className={`mt-4 text-sm font-medium ${
              isWrong ? "text-clay" : "text-sage-deep"
            }`}
          >
            {lastMessage}
          </p>
        )}

        {/* Hint */}
        {lastHint && (
          <div className="mt-3 rounded-xl border border-ochre/40 bg-ochre/5 px-4 py-3">
            <p className="text-xs font-semibold text-ochre">提示</p>
            <p className="mt-1 text-sm text-ink-soft">{lastHint}</p>
          </div>
        )}

        {/* Attempts counter */}
        {attempts > 0 && (
          <p className="mt-2 text-xs text-ink-soft">
            已尝试 {attempts} 次
          </p>
        )}
      </div>

      {/* Action buttons: Submit / Hint / Skip */}
      <div className="flex gap-3">
        {isSingleChoice && puzzle.options && (
          <button
            type="button"
            disabled={disabled || !selected}
            onClick={handleSubmit}
            className="flex-1 rounded-full bg-sage-deep px-5 py-3 text-sm font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99] disabled:opacity-40"
          >
            提交答案
          </button>
        )}

        <button
          type="button"
          disabled={disabled}
          onClick={onRequestHint}
          className="rounded-full border border-line bg-paper px-4 py-3 text-sm text-ink-soft transition hover:border-sage hover:text-ink disabled:opacity-40"
        >
          提示
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={onSkip}
          className="rounded-full border border-line bg-paper px-4 py-3 text-sm text-ink-soft transition hover:border-clay hover:text-clay disabled:opacity-40"
        >
          跳过
        </button>
      </div>
    </div>
  );
}
