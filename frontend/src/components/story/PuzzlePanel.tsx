import { useState } from "react";
import { SkipPuzzleDialog } from "@/features/story/components/SkipPuzzleDialog";
import { StoryPuzzleRenderer } from "@/features/story/puzzles";
import type { StoryPuzzleData } from "@/features/story/types";
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

const SUPPORTED_TYPES = new Set([
  "single_choice",
  "multi_select",
  "mapping",
  "evidence_chain",
  "assembly",
]);

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
  const [confirmingSkip, setConfirmingSkip] = useState(false);
  const supported = SUPPORTED_TYPES.has(puzzle.type);

  return (
    <div className="space-y-4">
      {supported ? (
        <StoryPuzzleRenderer
          key={puzzle.id}
          puzzle={puzzle as unknown as StoryPuzzleData}
          disabled={disabled}
          onSubmit={onSubmitAnswer}
        />
      ) : (
        <div className="rounded-2xl border border-clay/30 bg-clay/5 p-4">
          <p className="text-base text-clay">
            暂不支持此谜题类型：{puzzle.type}
          </p>
        </div>
      )}

      {lastMessage && (
        <div
          role="status"
          className="rounded-xl border border-sage/35 bg-sage/10 px-4 py-3"
        >
          <p className="text-base leading-7 text-ink">{lastMessage}</p>
        </div>
      )}

      {lastHint && (
        <div className="rounded-xl border border-ochre/40 bg-ochre/5 px-4 py-3">
          <p className="text-[13px] font-semibold text-ochre">阿莲的提示</p>
          <p className="mt-1 text-base leading-7 text-ink-soft">{lastHint}</p>
        </div>
      )}

      {attempts > 0 && (
        <p className="text-[13px] text-ink-soft">已尝试 {attempts} 次</p>
      )}

      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          disabled={disabled}
          onClick={onRequestHint}
          className="min-h-12 rounded-full border border-line bg-paper px-4 text-base text-ink-soft transition disabled:opacity-40"
        >
          提示
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => setConfirmingSkip(true)}
          className="min-h-12 rounded-full border border-line bg-paper px-4 text-base text-ink-soft transition disabled:opacity-40"
        >
          跳过
        </button>
      </div>

      <SkipPuzzleDialog
        open={confirmingSkip}
        busy={disabled}
        message={puzzle.skip_text}
        onCancel={() => setConfirmingSkip(false)}
        onConfirm={() => {
          setConfirmingSkip(false);
          onSkip();
        }}
      />
    </div>
  );
}
