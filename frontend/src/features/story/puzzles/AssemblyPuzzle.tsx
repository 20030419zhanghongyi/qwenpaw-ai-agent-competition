import { useEffect, useMemo, useState } from "react";
import { StoryImage } from "../assets";
import type { AssemblyPuzzleData, StoryPuzzleOption } from "../types";
import { PuzzleFrame } from "./PuzzleFrame";
import { usePointerDrag } from "./usePointerDrag";
import { useStoryMessages } from "../storyI18n";

interface AssemblyPuzzleProps {
  puzzle: AssemblyPuzzleData;
  disabled?: boolean;
  onSubmit: (answer: string[]) => void;
}

const DEFAULT_PIECE_ASSET_IDS: Readonly<Record<string, string>> = {
  upper_frame: "V4-LOU-P01",
  lower_frame: "V4-LOU-P02",
  oyster_shell_panel: "V4-LOU-P03",
  wooden_shutter: "V4-LOU-P04",
  stained_glass: "V4-LOU-P05",
  iron_grille: "V4-LOU-P06",
  aluminum_frame: "V4-LOU-P07",
  stone_lattice: "V4-LOU-P08",
};

function PieceVisual({
  piece,
  fallbackIndex,
}: {
  piece: StoryPuzzleOption;
  fallbackIndex: number;
}) {
  const st = useStoryMessages();
  const assetId = piece.asset_id ?? DEFAULT_PIECE_ASSET_IDS[piece.id];

  return (
    <>
      {assetId ? (
        <StoryImage
          assetId={assetId}
          alt={piece.text}
          className="mx-auto mb-1 w-14 rounded-lg"
          imageClassName="object-contain"
        />
      ) : (
        <span className="mx-auto mb-2 flex size-14 flex-col items-center justify-center rounded-lg border border-line bg-[url('/story/v4/_placeholder.svg')] bg-cover px-1 text-center text-[10px] leading-3 text-ink-soft">
          <span>
            {import.meta.env.DEV ? st("pieceImageMissing") : st("pieceImageUnavailable")}
          </span>
          {import.meta.env.DEV ? (
            <span className="mt-0.5 max-w-full break-all font-mono text-[8px] leading-[10px] text-ink-soft/70">
              {piece.id || `piece-${fallbackIndex + 1}`}
            </span>
          ) : null}
        </span>
      )}
      <span>{piece.text}</span>
    </>
  );
}

export function AssemblyPuzzle({
  puzzle,
  disabled = false,
  onSubmit,
}: AssemblyPuzzleProps) {
  const st = useStoryMessages();
  const slotCount = Math.max(
    1,
    Math.min(puzzle.slot_count ?? 4, puzzle.options.length),
  );
  const [slots, setSlots] = useState<Array<string | null>>(
    Array.from({ length: slotCount }, () => null),
  );
  const [activePiece, setActivePiece] = useState<string | null>(null);
  const [hoveredSlot, setHoveredSlot] = useState<number | null>(null);

  useEffect(() => {
    setSlots(Array.from({ length: slotCount }, () => null));
    setActivePiece(null);
    setHoveredSlot(null);
  }, [puzzle.id, slotCount]);

  const pieceInSlot = (pieceId: string) => slots.includes(pieceId);
  const place = (slotIndex: number, pieceId: string) => {
    setSlots((current) => {
      const next = current.map((value) => (value === pieceId ? null : value));
      next[slotIndex] = pieceId;
      return next;
    });
    setActivePiece(null);
    setHoveredSlot(null);
  };

  const slotAtPoint = (x: number, y: number): number | null => {
    const slot = document
      .elementFromPoint(x, y)
      ?.closest<HTMLElement>("[data-assembly-slot]");
    const rawIndex = slot?.dataset.assemblySlot;
    if (rawIndex == null) return null;
    const index = Number(rawIndex);
    return Number.isInteger(index) ? index : null;
  };

  const { drag, handleProps } = usePointerDrag({
    disabled,
    onMove: (_pieceId, x, y) => setHoveredSlot(slotAtPoint(x, y)),
    onEnd: (pieceId, x, y) => {
      const targetSlot = slotAtPoint(x, y);
      if (targetSlot != null) place(targetSlot, pieceId);
      else setHoveredSlot(null);
    },
  });
  const draggedPiece = useMemo(
    () => puzzle.options.find((piece) => piece.id === drag?.id),
    [drag?.id, puzzle.options],
  );

  return (
    <>
      <PuzzleFrame
        prompt={puzzle.prompt}
        selectionHint={st("assemblyHint", { count: slotCount })}
        canSubmit={slots.every(Boolean)}
        disabled={disabled}
        onSubmit={() => onSubmit(slots.filter((id): id is string => Boolean(id)))}
      >
        <div className="rounded-xl border border-dashed border-sage/50 bg-sage/5 p-3">
          <p className="text-[13px] font-medium text-ink-soft">{st("targetOutline")}</p>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {slots.map((pieceId, index) => {
              const piece = puzzle.options.find((item) => item.id === pieceId);
              return (
                <button
                  key={puzzle.slots?.[index]?.id ?? index}
                  type="button"
                  data-assembly-slot={index}
                  disabled={disabled}
                  onClick={() => {
                    if (activePiece) place(index, activePiece);
                    else if (pieceId) {
                      setSlots((current) =>
                        current.map((value, valueIndex) =>
                          valueIndex === index ? null : value,
                        ),
                      );
                    }
                  }}
                  className={`relative min-h-28 rounded-xl border p-2 text-center transition ${
                    hoveredSlot === index
                      ? "scale-[1.02] border-ochre bg-ochre/15 ring-2 ring-ochre/35"
                      : piece
                        ? "border-sage-deep bg-card"
                        : activePiece
                          ? "border-ochre bg-ochre/10"
                          : "border-line bg-paper/70"
                  }`}
                  aria-label={
                    piece
                      ? st("filledSlotAria", { index: index + 1, item: piece.text })
                      : st("emptySlotAria", {
                          index: index + 1,
                          action: activePiece ? st("placeSelectedPiece") : "",
                        })
                  }
                >
                  <span className="absolute left-2 top-2 grid size-6 place-items-center rounded-full bg-paper text-xs text-ink-soft">
                    {index + 1}
                  </span>
                  {piece ? (
                    <span className="flex h-full flex-col items-center justify-center gap-1 pt-5 text-sm text-ink">
                      <PieceVisual
                        piece={piece}
                        fallbackIndex={puzzle.options.indexOf(piece)}
                      />
                    </span>
                  ) : (
                    <span className="text-[13px] text-ink-soft">
                      {hoveredSlot === index
                        ? st("releaseToPlace")
                        : puzzle.slots?.[index]?.label ?? st("placePiece")}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-5">
          <p className="text-[13px] font-medium text-ink-soft">{st("pieceTray")}</p>
          <div className="mt-2 flex snap-x gap-2 overflow-x-auto pb-2">
            {puzzle.options.map((piece, index) => {
              const placed = pieceInSlot(piece.id);
              const active = activePiece === piece.id;
              return (
                <div
                  key={piece.id}
                  data-drag-preview
                  className={`w-28 shrink-0 snap-start overflow-hidden rounded-xl border ${
                    active
                      ? "border-ochre bg-ochre/10 text-ochre"
                      : "border-line bg-paper text-ink"
                  } ${drag?.id === piece.id ? "opacity-35" : ""}`}
                >
                  <button
                    type="button"
                    disabled={disabled || placed}
                    aria-pressed={active}
                    onClick={() =>
                      setActivePiece((current) =>
                        current === piece.id ? null : piece.id,
                      )
                    }
                    className="flex min-h-28 w-full flex-col items-center justify-center p-2 text-sm disabled:opacity-35"
                  >
                    <PieceVisual piece={piece} fallbackIndex={index} />
                  </button>
                  <button
                    type="button"
                    disabled={disabled || placed}
                    {...handleProps(piece.id)}
                    className="inline-flex min-h-11 w-full touch-none select-none items-center justify-center gap-1 border-t border-line bg-card/80 text-[13px] text-ink-soft disabled:opacity-35"
                    aria-label={st("holdToDrag", { item: piece.text })}
                  >
                    <span aria-hidden>⠿</span>
                    {placed ? st("placed") : st("drag")}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </PuzzleFrame>

      {drag && draggedPiece && (
        <div
          className="pointer-events-none fixed z-[80] flex min-h-28 flex-col items-center justify-center rounded-xl border border-ochre/60 bg-paper p-2 text-center text-sm text-ink opacity-95 shadow-[var(--shadow-lift)]"
          style={{
            left: drag.x - drag.grabX,
            top: drag.y - drag.grabY,
            width: drag.width,
          }}
          aria-hidden
        >
          <PieceVisual
            piece={draggedPiece}
            fallbackIndex={puzzle.options.indexOf(draggedPiece)}
          />
        </div>
      )}
    </>
  );
}
