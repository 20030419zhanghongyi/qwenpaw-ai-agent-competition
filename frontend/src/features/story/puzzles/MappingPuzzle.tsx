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
  const accessibleInstructionsId = `mapping-accessible-instructions-${puzzle.id}`;

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

  const clearAssignment = (fieldId: string) => {
    setMapping((current) => {
      const next = { ...current };
      delete next[fieldId];
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
        <p
          id={accessibleInstructionsId}
          className="text-xs leading-5 text-ink-soft"
        >
          {st("mappingAccessibleInstructions")}
        </p>
        {puzzle.fields.map((field) => {
          const groupName = `mapping-${puzzle.id}-${field.id}`;
          return (
            <fieldset
              key={field.id}
              aria-describedby={accessibleInstructionsId}
              className="min-w-0 rounded-xl border border-line bg-paper-warm/40 p-3"
            >
              <legend className="px-1 text-sm font-semibold text-ink">
                {field.label}
              </legend>
              <div className="mt-1 space-y-2">
                <label className="flex min-w-0 cursor-pointer items-start gap-2 rounded-lg border border-line bg-paper px-3 py-2.5 text-sm text-ink">
                  <input
                    type="radio"
                    name={groupName}
                    value=""
                    checked={!mapping[field.id]}
                    disabled={disabled}
                    onChange={() => clearAssignment(field.id)}
                    className="mt-0.5 size-4 shrink-0 accent-sage-deep"
                  />
                  <span className="min-w-0 whitespace-normal break-words leading-5">
                    {st("notSelected")}
                  </span>
                </label>
                {puzzle.options.map((option) => {
                  const owner = optionOwner(option.id);
                  const selected = mapping[field.id] === option.id;
                  const ownedByOtherField = Boolean(owner && owner !== field.id);
                  const ownerLabel = puzzle.fields.find(
                    (candidate) => candidate.id === owner,
                  )?.label;
                  return (
                    <label
                      key={option.id}
                      className={`flex min-w-0 items-start gap-2 rounded-lg border px-3 py-2.5 text-sm transition ${
                        selected
                          ? "border-sage-deep bg-sage-deep/10 text-sage-deep"
                          : "border-line bg-paper text-ink"
                      } ${
                        disabled || ownedByOtherField
                          ? "cursor-not-allowed opacity-50"
                          : "cursor-pointer"
                      }`}
                    >
                      <input
                        type="radio"
                        name={groupName}
                        value={option.id}
                        checked={selected}
                        disabled={disabled || ownedByOtherField}
                        onChange={() => assign(field.id, option.id)}
                        className="mt-0.5 size-4 shrink-0 accent-sage-deep"
                      />
                      <span className="min-w-0 whitespace-normal break-words leading-5">
                        {option.text}
                        {ownedByOtherField && ownerLabel && (
                          <span className="mt-0.5 block text-xs text-ink-soft">
                            {st("mappingPairedTo", { label: ownerLabel })}
                          </span>
                        )}
                      </span>
                    </label>
                  );
                })}
              </div>
            </fieldset>
          );
        })}
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
