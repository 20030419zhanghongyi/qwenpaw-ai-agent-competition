import { useEffect, useState } from "react";
import type { MultiSelectPuzzleData } from "../types";
import { PuzzleFrame } from "./PuzzleFrame";
import { useStoryMessages } from "../storyI18n";

interface MultiSelectPuzzleProps {
  puzzle: MultiSelectPuzzleData;
  disabled?: boolean;
  submitLabel?: string;
  onSubmit: (answer: string[]) => void;
}

export function MultiSelectPuzzle({
  puzzle,
  disabled = false,
  submitLabel,
  onSubmit,
}: MultiSelectPuzzleProps) {
  const st = useStoryMessages();
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => setSelected([]), [puzzle.id]);

  const toggle = (optionId: string) => {
    setSelected((current) => {
      if (current.includes(optionId)) {
        return current.filter((id) => id !== optionId);
      }
      if (
        puzzle.max_selections != null &&
        current.length >= puzzle.max_selections
      ) {
        return current;
      }
      return [...current, optionId];
    });
  };

  const enough =
    selected.length > 0 &&
    (puzzle.min_selections == null ||
      selected.length >= puzzle.min_selections);

  return (
    <PuzzleFrame
      prompt={puzzle.prompt}
      selectionHint={
        puzzle.max_selections
          ? st("multiChoiceMax", { max: puzzle.max_selections, count: selected.length })
          : st("multiChoiceCount", { count: selected.length })
      }
      canSubmit={enough}
      disabled={disabled}
      submitLabel={submitLabel}
      onSubmit={() => onSubmit([...selected])}
    >
      <div className="space-y-2" role="group" aria-label={st("multiChoiceOptions")}>
        {puzzle.options.map((option) => {
          const active = selected.includes(option.id);
          return (
            <button
              key={option.id}
              type="button"
              disabled={disabled}
              aria-pressed={active}
              onClick={() => toggle(option.id)}
              className={`flex min-h-12 w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-base transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage ${
                active
                  ? "border-sage-deep bg-sage-deep/10 text-sage-deep"
                  : "border-line bg-paper text-ink"
              } disabled:opacity-45`}
            >
              <span
                className={`grid size-6 shrink-0 place-items-center rounded-md border text-sm ${
                  active
                    ? "border-sage-deep bg-sage-deep text-paper"
                    : "border-line bg-card"
                }`}
                aria-hidden
              >
                {active ? "✓" : ""}
              </span>
              <span>{option.text}</span>
            </button>
          );
        })}
      </div>
    </PuzzleFrame>
  );
}
