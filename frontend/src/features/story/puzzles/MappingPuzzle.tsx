import { useEffect, useState } from "react";
import type { MappingPuzzleData } from "../types";
import { PuzzleFrame } from "./PuzzleFrame";
import { useStoryMessages } from "../storyI18n";

interface MappingPuzzleProps {
  puzzle: MappingPuzzleData;
  disabled?: boolean;
  onSubmit: (answer: Record<string, string>) => void;
}

const PAIR_STYLES = [
  "border-sage-deep bg-sage-deep/10 text-sage-deep",
  "border-ochre bg-ochre/10 text-ochre",
  "border-clay bg-clay/10 text-clay",
  "border-moss bg-moss/10 text-moss",
  "border-sage bg-sage/10 text-sage-deep",
];

export function MappingPuzzle({
  puzzle,
  disabled = false,
  onSubmit,
}: MappingPuzzleProps) {
  const st = useStoryMessages();
  const [activeField, setActiveField] = useState<string | null>(
    puzzle.fields[0]?.id ?? null,
  );
  const [mapping, setMapping] = useState<Record<string, string>>({});

  useEffect(() => {
    setActiveField(puzzle.fields[0]?.id ?? null);
    setMapping({});
  }, [puzzle.id]);

  const optionOwner = (optionId: string) =>
    Object.entries(mapping).find(([, value]) => value === optionId)?.[0];

  const assign = (fieldId: string, optionId: string) => {
    setMapping((current) => {
      const next = { ...current };
      const previousOwner = optionOwnerFrom(current, optionId);
      if (previousOwner) delete next[previousOwner];
      if (next[fieldId] === optionId) delete next[fieldId];
      else next[fieldId] = optionId;
      return next;
    });
  };

  return (
    <PuzzleFrame
      prompt={puzzle.prompt}
      selectionHint={st("mappingHint")}
      canSubmit={puzzle.fields.every((field) => Boolean(mapping[field.id]))}
      disabled={disabled}
      onSubmit={() => onSubmit({ ...mapping })}
    >
      <fieldset>
        <legend className="text-[13px] font-medium text-ink-soft">
          {st("mappingStepOne")}
        </legend>
        <div className="mt-2 grid grid-cols-5 gap-1.5">
          {puzzle.fields.map((field, index) => {
            const assigned = mapping[field.id];
            return (
              <button
                key={field.id}
                type="button"
                disabled={disabled}
                aria-pressed={activeField === field.id}
                onClick={() => setActiveField(field.id)}
                className={`min-h-12 rounded-xl border px-1 text-sm font-medium ${
                  activeField === field.id || assigned
                    ? PAIR_STYLES[index % PAIR_STYLES.length]
                    : "border-line bg-paper text-ink"
                }`}
              >
                {field.label}
                {assigned && (
                  <span className="block text-[10px]" aria-hidden>
                    {index + 1}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </fieldset>

      <fieldset className="mt-4">
        <legend className="text-[13px] font-medium text-ink-soft">
          {st("mappingStepTwo")}
        </legend>
        <div className="mt-2 space-y-2">
          {puzzle.options.map((option) => {
            const owner = optionOwner(option.id);
            const ownerIndex = puzzle.fields.findIndex(
              (field) => field.id === owner,
            );
            return (
              <button
                key={option.id}
                type="button"
                disabled={disabled || !activeField}
                onClick={() => activeField && assign(activeField, option.id)}
                className={`min-h-12 w-full rounded-xl border px-4 py-3 text-left text-base ${
                  owner
                    ? PAIR_STYLES[ownerIndex % PAIR_STYLES.length]
                    : "border-line bg-paper text-ink"
                } disabled:opacity-45`}
              >
                {owner && (
                  <span className="mr-2 font-semibold">
                    {ownerIndex + 1}.
                  </span>
                )}
                {option.text}
              </button>
            );
          })}
        </div>
      </fieldset>

      <div className="mt-4 space-y-2 border-t border-line pt-4">
        <p className="text-[13px] font-medium text-ink-soft">
          {st("accessibleSelection")}
        </p>
        {puzzle.fields.map((field) => (
          <label
            key={field.id}
            className="grid grid-cols-[5rem_1fr] items-center gap-2 text-sm text-ink"
          >
            <span>{field.label}</span>
            <select
              value={mapping[field.id] ?? ""}
              disabled={disabled}
              onChange={(event) => {
                const optionId = event.target.value;
                if (!optionId) {
                  setMapping((current) => {
                    const next = { ...current };
                    delete next[field.id];
                    return next;
                  });
                } else {
                  assign(field.id, optionId);
                }
              }}
              className="min-h-11 rounded-xl border border-line bg-paper px-3 text-base text-ink"
            >
              <option value="">{st("notSelected")}</option>
              {puzzle.options.map((option) => {
                const owner = optionOwner(option.id);
                return (
                  <option
                    key={option.id}
                    value={option.id}
                    disabled={Boolean(owner && owner !== field.id)}
                  >
                    {option.text}
                  </option>
                );
              })}
            </select>
          </label>
        ))}
      </div>
    </PuzzleFrame>
  );
}

function optionOwnerFrom(
  mapping: Record<string, string>,
  optionId: string,
): string | undefined {
  return Object.entries(mapping).find(([, value]) => value === optionId)?.[0];
}
