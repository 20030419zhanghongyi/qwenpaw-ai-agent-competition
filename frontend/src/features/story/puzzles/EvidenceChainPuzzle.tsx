import { useEffect, useMemo, useState } from "react";
import { StoryImage } from "../assets";
import { StoryImageViewer } from "../components/StoryImageViewer";
import type {
  EvidenceChainPuzzleData,
  StoryPuzzleOption,
} from "../types";
import { PuzzleFrame } from "./PuzzleFrame";
import { usePointerDrag } from "./usePointerDrag";

interface EvidenceChainPuzzleProps {
  puzzle: EvidenceChainPuzzleData;
  disabled?: boolean;
  onSubmit: (answer: string[]) => void;
}

interface EvidencePresentation {
  description: string;
  sourceLabel: string;
  assetId: string;
}

const SAM_KAI_EVIDENCE: Record<string, EvidencePresentation> = {
  delivery_order: {
    description: "记录货物从梁掌柜处交付出去的起点。",
    sourceLabel: "交货方记录",
    assetId: "V4-SAM-02",
  },
  store_ledger: {
    description: "记录陈掌柜店内实际登记收进的货物。",
    sourceLabel: "收货方账簿",
    assetId: "V4-SAM-03",
  },
  porter_receipt: {
    description: "记录脚夫阿成对中途寄存货物的说明。",
    sourceLabel: "经手人存条",
    assetId: "V4-SAM-04",
  },
  single_summary: {
    description: "后来人根据已有材料写下的二手概括。",
    sourceLabel: "后人整理",
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

function presentation(option: StoryPuzzleOption): EvidencePresentation {
  const fallback = SAM_KAI_EVIDENCE[option.id];
  return {
    description:
      option.description ?? fallback?.description ?? "查看这份材料所记录的环节。",
    sourceLabel:
      option.source_label ?? fallback?.sourceLabel ?? "剧情证据材料",
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
  const detail = presentation(option);
  return (
    <div className="grid grid-cols-[5rem_minmax(0,1fr)] items-start gap-3">
      <StoryImage
        assetId={detail.assetId}
        alt={`${option.text}对应材料`}
        className="rounded-xl"
        imageClassName="object-cover"
        onOpen={
          onOpen
            ? (assetId) => onOpen(assetId, `${option.text}对应材料`)
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
          来源类型：{detail.sourceLabel}
        </span>
      </div>
    </div>
  );
}

export function EvidenceChainPuzzle({
  puzzle,
  disabled = false,
  onSubmit,
}: EvidenceChainPuzzleProps) {
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
        selectionHint={`选择 ${requiredCount} 份能互相验证的材料，长按拖动或使用按钮调整顺序。后端会判断证据链。`}
        canSubmit={chain.length >= requiredCount}
        disabled={disabled}
        onSubmit={() => onSubmit(chain.map((item) => item.id))}
      >
        <div>
          <p className="text-[13px] font-medium text-ink-soft">候选材料</p>
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
                  加入证据链
                </button>
              </div>
            ))}
            {candidates.length === 0 && (
              <p className="rounded-xl border border-dashed border-line p-3 text-center text-[13px] text-ink-soft">
                所有材料都已放入证据链
              </p>
            )}
          </div>
        </div>

        <div className="mt-5">
          <p className="text-[13px] font-medium text-ink-soft">
            当前证据链，共 {chain.length} 项
          </p>
          <ol className="mt-2 space-y-3" aria-label="可排序的证据链">
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
                    证据链第 {index + 1} 项
                  </p>
                  <button
                    type="button"
                    disabled={disabled}
                    {...handleProps(option.id)}
                    className="inline-flex min-h-11 touch-none select-none items-center gap-1 rounded-full border border-line bg-card px-3 text-[13px] text-ink-soft disabled:opacity-35"
                    aria-label={`长按拖动${option.text}`}
                  >
                    <span aria-hidden>⠿</span>
                    拖动
                  </button>
                </div>

                <EvidenceCardContent option={option} onOpen={openEvidence} />

                <div className="mt-3 grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    disabled={disabled || index === 0}
                    onClick={() => moveBy(index, -1)}
                    className="min-h-11 rounded-full border border-line bg-card text-sm text-ink disabled:opacity-35"
                    aria-label={`上移${option.text}`}
                  >
                    上移
                  </button>
                  <button
                    type="button"
                    disabled={disabled || index === chain.length - 1}
                    onClick={() => moveBy(index, 1)}
                    className="min-h-11 rounded-full border border-line bg-card text-sm text-ink disabled:opacity-35"
                    aria-label={`下移${option.text}`}
                  >
                    下移
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
                    aria-label={`移除${option.text}`}
                  >
                    移除
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
