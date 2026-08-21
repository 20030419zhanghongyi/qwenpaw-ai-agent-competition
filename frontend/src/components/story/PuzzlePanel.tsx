import { useEffect, useState } from "react";
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
  const [selectedMany, setSelectedMany] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const options = puzzle.options ?? [];
  const isSingleChoice = puzzle.type === "single_choice";
  const isMapping = puzzle.type === "mapping";
  const isMultiChoice =
    puzzle.type === "multi_select" ||
    puzzle.type === "evidence_chain" ||
    puzzle.type === "assembly";
  const isWrong = lastMessage && !lastMessage.includes("正确") && attempts > 0;

  useEffect(() => {
    setSelected(null);
    setSelectedMany([]);
    setMapping({});
  }, [puzzle.id]);

  const handleSubmit = () => {
    if (isSingleChoice && selected) {
      onSubmitAnswer(selected);
    } else if (isMultiChoice && selectedMany.length > 0) {
      onSubmitAnswer(selectedMany);
    } else if (isMapping && puzzle.fields) {
      onSubmitAnswer(mapping);
    }
  };

  const toggleMany = (optionId: string) => {
    setSelectedMany((current) =>
      current.includes(optionId)
        ? current.filter((id) => id !== optionId)
        : [...current, optionId],
    );
  };

  const canSubmit =
    (isSingleChoice && !!selected) ||
    (isMultiChoice && selectedMany.length > 0) ||
    (isMapping &&
      !!puzzle.fields?.length &&
      puzzle.fields.every((field) => !!mapping[field.id]));

  return (
    <div className="space-y-4">
      {/* Puzzle prompt */}
      <div className="rounded-2xl border border-line bg-card p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sage-deep">
          谜题
        </p>
        <p className="mt-2 text-sm leading-relaxed text-ink">{puzzle.prompt}</p>

        {/* Single choice options */}
        {isSingleChoice && options.length > 0 && (
          <div className="mt-4 space-y-2.5">
            {options.map((opt) => {
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

        {/* Multi select, evidence chain, and assembly options */}
        {isMultiChoice && options.length > 0 && (
          <div className="mt-4 space-y-2.5">
            {typeof puzzle.required_count === "number" && (
              <p className="text-xs text-ink-soft">
                请选择 {puzzle.required_count} 项
              </p>
            )}
            {options.map((opt) => {
              const isSelected = selectedMany.includes(opt.id);
              return (
                <button
                  key={opt.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => toggleMany(opt.id)}
                  className={`flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left text-sm transition ${
                    isSelected
                      ? "border-sage-deep bg-sage-deep/10 text-sage-deep font-medium"
                      : "border-line bg-paper hover:border-sage"
                  } disabled:opacity-50`}
                >
                  <span
                    className={`mt-0.5 grid size-4 shrink-0 place-items-center rounded border text-[10px] ${
                      isSelected
                        ? "border-sage-deep bg-sage-deep text-paper"
                        : "border-line bg-card text-transparent"
                    }`}
                    aria-hidden
                  >
                    ✓
                  </span>
                  <span>{opt.text}</span>
                </button>
              );
            })}
          </div>
        )}

        {/* Mapping fields */}
        {isMapping && puzzle.fields && options.length > 0 && (
          <div className="mt-4 space-y-3">
            {puzzle.fields.map((field) => (
              <label key={field.id} className="block">
                <span className="text-xs font-semibold text-sage-deep">
                  {field.label}
                </span>
                <select
                  disabled={disabled}
                  value={mapping[field.id] ?? ""}
                  onChange={(event) =>
                    setMapping((current) => ({
                      ...current,
                      [field.id]: event.target.value,
                    }))
                  }
                  className="mt-1 w-full rounded-xl border border-line bg-paper px-3 py-2.5 text-sm text-ink focus:border-sage-deep focus:outline-none disabled:opacity-50"
                >
                  <option value="">请选择</option>
                  {options.map((opt) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.text}
                    </option>
                  ))}
                </select>
              </label>
            ))}
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
        {(isSingleChoice || isMultiChoice || isMapping) && (
          <button
            type="button"
            disabled={disabled || !canSubmit}
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
