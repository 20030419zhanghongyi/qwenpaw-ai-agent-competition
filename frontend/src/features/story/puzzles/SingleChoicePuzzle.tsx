import { useEffect, useState } from "react";
import type { LegacySingleChoicePuzzleData } from "../types";
import { PuzzleFrame } from "./PuzzleFrame";

interface SingleChoicePuzzleProps {
  puzzle: LegacySingleChoicePuzzleData;
  disabled?: boolean;
  onSubmit: (answer: string) => void;
}

export function SingleChoicePuzzle({
  puzzle,
  disabled = false,
  onSubmit,
}: SingleChoicePuzzleProps) {
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => setSelected(null), [puzzle.id]);

  return (
    <PuzzleFrame
      prompt={puzzle.prompt}
      canSubmit={Boolean(selected)}
      disabled={disabled}
      onSubmit={() => selected && onSubmit(selected)}
    >
      <div className="space-y-2" role="radiogroup" aria-label="单选题选项">
        {puzzle.options.map((option) => (
          <button
            key={option.id}
            type="button"
            role="radio"
            aria-checked={selected === option.id}
            disabled={disabled}
            onClick={() => setSelected(option.id)}
            className={`min-h-12 w-full rounded-xl border px-4 py-3 text-left text-base ${
              selected === option.id
                ? "border-sage-deep bg-sage-deep/10 text-sage-deep"
                : "border-line bg-paper text-ink"
            }`}
          >
            {option.text}
          </button>
        ))}
      </div>
    </PuzzleFrame>
  );
}
