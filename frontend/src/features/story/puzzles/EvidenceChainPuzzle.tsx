import { useEffect, useMemo, useState } from "react";
import { StoryImage } from "../assets";
import { StoryImageViewer } from "../components/StoryImageViewer";
import type {
  EvidenceChainPuzzleData,
  StoryPuzzleOption,
} from "../types";
import { PuzzleFrame } from "./PuzzleFrame";
import { usePointerDrag } from "./usePointerDrag";
import { useStoryMessages, type StoryMessageKey } from "../storyI18n";

interface EvidenceChainPuzzleProps {
  puzzle: EvidenceChainPuzzleData;
  disabled?: boolean;
  submitLabel?: string;
  onSubmit: (answer: string[]) => void;
}

interface EvidenceConfig {
  descriptionKey: StoryMessageKey;
  sourceKey: StoryMessageKey;
  assetId: string;
}

interface EvidencePresentation {
  description: string;
  sourceLabel: string;
  assetId: string;
}

const SAM_KAI_EVIDENCE: Record<string, EvidenceConfig> = {
  delivery_order: {
    descriptionKey: "evidenceDeliveryDescription",
    sourceKey: "evidenceDeliverySource",
    assetId: "V4-SAM-02",
  },
  store_ledger: {
    descriptionKey: "evidenceLedgerDescription",
    sourceKey: "evidenceLedgerSource",
    assetId: "V4-SAM-03",
  },
  porter_receipt: {
    descriptionKey: "evidenceReceiptDescription",
    sourceKey: "evidenceReceiptSource",
    assetId: "V4-SAM-04",
  },
  single_summary: {
    descriptionKey: "evidenceSummaryDescription",
    sourceKey: "evidenceSummarySource",
    assetId: "V4-SAM-05",
  },
};

function move<T>(items: T[], from: number, to: number): T[] {
  if (from === to || from < 0 || to < 0) return items;
  const next = [...items];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

function presentation(
  option: StoryPuzzleOption,
  fallbackDescription: string,
  fallbackSource: string,
  localizedDescription?: string,
  localizedSource?: string,
): EvidencePresentation {
  const fallback = SAM_KAI_EVIDENCE[option.id];
  return {
    description: option.description ?? localizedDescription ?? fallbackDescription,
    sourceLabel: option.source_label ?? localizedSource ?? fallbackSource,
    assetId: option.asset_id ?? fallback?.assetId ?? "V4-SAM-05",
  };
}

function EvidenceCardContent({
  option,
  onOpen,
}: {
  option: StoryPuzzleOption;
  onOpen?: (assetId: string, alt: string) => void;
}) {
  const st = useStoryMessages();
  const evidence = SAM_KAI_EVIDENCE[option.id];
  const detail = presentation(
    option,
    st("evidenceFallbackDescription"),
    st("evidenceFallbackSource"),
    evidence ? st(evidence.descriptionKey) : undefined,
    evidence ? st(evidence.sourceKey) : undefined,
  );
  const imageAlt = st("evidenceImageAlt", { item: option.text });
  return (
    <div className="grid grid-cols-[5rem_minmax(0,1fr)] items-start gap-3">
      <StoryImage
        assetId={detail.assetId}
        alt={imageAlt}
        className="rounded-xl"
        imageClassName="object-cover"
        onOpen={
          onOpen
            ? (assetId) => onOpen(assetId, imageAlt)
            : undefined
        }
      />
      <div className="min-w-0">
        <p className="text-base font-semibold leading-6 text-ink">
          {option.text}
        </p>
        <p className="mt-1 text-[13px] leading-5 text-ink-soft">
          {detail.description}
        </p>
        <span className="mt-2 inline-flex min-h-6 items-center rounded-full border border-sage/30 bg-sage/10 px-2 text-[11px] font-medium text-sage-deep">
          {st("sourceType", { label: detail.sourceLabel })}
        </span>
      </div>
    </div>
  );
}

export function EvidenceChainPuzzle({
  puzzle,
  disabled = false,
  submitLabel,
  onSubmit,
}: EvidenceChainPuzzleProps) {
  const st = useStoryMessages();
  const [chain, setChain] = useState<StoryPuzzleOption[]>([]);
  const [viewer, setViewer] = useState<{ assetId: string; alt: string } | null>(
    null,
  );

  useEffect(() => setChain([]), [puzzle.id]);

  const candidates = puzzle.options.filter(
    (option) => !chain.some((item) => item.id === option.id),
  );
  const requiredCount =
    puzzle.required_count ??
    (puzzle.id === "puzzle_evidence_chain" ? 3 : 1);

  const moveBy = (index: number, delta: number) => {
    setChain((current) =>
      move(
        current,
        index,
        Math.max(0, Math.min(current.length - 1, index + delta)),
      ),
    );
  };

  const { drag, handleProps } = usePointerDrag({
    disabled,
    onMove: (sourceId, x, y) => {
      const target = document
        .elementFromPoint(x, y)
        ?.closest<HTMLElement>("[data-evidence-id]");
      const targetId = target?.dataset.evidenceId;
      if (!targetId || targetId === sourceId) return;
      setChain((current) => {
        const from = current.findIndex((item) => item.id === sourceId);
        const to = current.findIndex((item) => item.id === targetId);
        return move(current, from, to);
      });
    },
  });
  const draggedOption = useMemo(
    () => chain.find((option) => option.id === drag?.id),
    [chain, drag?.id],
  );

  const openEvidence = (assetId: string, alt: string) =>
    setViewer({ assetId, alt });

  return (
    <>
      <PuzzleFrame
        prompt={puzzle.prompt}
        selectionHint={st("evidenceSelectionHint", { count: requiredCount })}
        canSubmit={chain.length >= requiredCount}
        disabled={disabled}
        submitLabel={submitLabel}
        onSubmit={() => onSubmit(chain.map((item) => item.id))}
      >
        <div>
          <p className="text-[13px] font-medium text-ink-soft">{st("candidates")}</p>
          <div className="mt-2 space-y-3">
            {candidates.map((option) => (
              <div
                key={option.id}
                className="rounded-2xl border border-line bg-paper p-3"
              >
                <EvidenceCardContent option={option} onOpen={openEvidence} />
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => setChain((current) => [...current, option])}
                  className="mt-3 min-h-11 w-full rounded-full border border-sage/35 bg-sage/10 px-4 text-sm font-medium text-sage-deep disabled:opacity-45"
                >
                  {st("addEvidence")}
                </button>
              </div>
            ))}
            {candidates.length === 0 && (
              <p className="rounded-xl border border-dashed border-line p-3 text-center text-[13px] text-ink-soft">
                {st("allEvidenceAdded")}
              </p>
            )}
          </div>
        </div>

        <div className="mt-5">
          <p className="text-[13px] font-medium text-ink-soft">
            {st("evidenceChainCount", { count: chain.length })}
          </p>
          <ol className="mt-2 space-y-3" aria-label={st("sortableEvidence")}>
            {chain.map((option, index) => (
              <li
                key={option.id}
                data-evidence-id={option.id}
                data-drag-preview
                className={`rounded-2xl border border-sage/35 bg-sage/10 p-3 transition ${
                  drag?.id === option.id
                    ? "opacity-35 ring-2 ring-ochre/40"
                    : ""
                }`}
              >
                <div className="mb-3 flex items-center gap-3">
                  <span className="grid size-8 shrink-0 place-items-center rounded-full bg-sage-deep font-serif text-sm font-bold text-paper">
                    {index + 1}
                  </span>
                  <p className="min-w-0 flex-1 text-[13px] font-medium text-sage-deep">
                    {st("evidenceChainItem", { index: index + 1 })}
                  </p>
                  <button
                    type="button"
                    disabled={disabled}
                    {...handleProps(option.id)}
                    className="inline-flex min-h-11 touch-none select-none items-center gap-1 rounded-full border border-line bg-card px-3 text-[13px] text-ink-soft disabled:opacity-35"
                    aria-label={st("dragItem", { item: option.text })}
                  >
                    <span aria-hidden>⠿</span>
                    {st("drag")}
                  </button>
                </div>

                <EvidenceCardContent option={option} onOpen={openEvidence} />

                <div className="mt-3 grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    disabled={disabled || index === 0}
                    onClick={() => moveBy(index, -1)}
                    className="min-h-11 rounded-full border border-line bg-card text-sm text-ink disabled:opacity-35"
                    aria-label={st("moveUpItem", { item: option.text })}
                  >
                    {st("moveUp")}
                  </button>
                  <button
                    type="button"
                    disabled={disabled || index === chain.length - 1}
                    onClick={() => moveBy(index, 1)}
                    className="min-h-11 rounded-full border border-line bg-card text-sm text-ink disabled:opacity-35"
                    aria-label={st("moveDownItem", { item: option.text })}
                  >
                    {st("moveDown")}
                  </button>
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() =>
                      setChain((current) =>
                        current.filter((item) => item.id !== option.id),
                      )
                    }
                    className="min-h-11 rounded-full border border-clay/30 bg-card text-sm text-clay disabled:opacity-35"
                    aria-label={`${st("remove")} ${option.text}`}
                  >
                    {st("remove")}
                  </button>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </PuzzleFrame>

      {drag && draggedOption && (
        <div
          className="pointer-events-none fixed z-[80] rounded-2xl border border-ochre/50 bg-paper p-3 opacity-95 shadow-[var(--shadow-lift)]"
          style={{
            left: drag.x - drag.grabX,
            top: drag.y - drag.grabY,
            width: drag.width,
          }}
          aria-hidden
        >
          <EvidenceCardContent option={draggedOption} />
        </div>
      )}

      <StoryImageViewer
        assetId={viewer?.assetId ?? null}
        alt={viewer?.alt}
        onClose={() => setViewer(null)}
      />
    </>
  );
}
