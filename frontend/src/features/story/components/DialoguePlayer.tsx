import { useEffect, useRef, useState } from "react";
import { StoryImage } from "../assets";
import type { StoryDialogueLine } from "../types";
import { DialogueBubble } from "./DialogueBubble";
import { useStoryMessages } from "../storyI18n";

interface DialoguePlayerProps {
  lines: StoryDialogueLine[];
  chapterId?: string;
  onComplete?: () => void;
  continueLabel?: string;
}

export function DialoguePlayer({
  lines,
  chapterId,
  onComplete,
  continueLabel,
}: DialoguePlayerProps) {
  const st = useStoryMessages();
  const resolvedContinueLabel = continueLabel ?? st("nextPanel");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const touchStartY = useRef<number | null>(null);
  const transitionTimer = useRef<number | null>(null);
  const completed = currentIndex >= lines.length - 1;
  const currentLine = lines[currentIndex];
  const historyLines = lines.slice(0, currentIndex);
  const dialogueKey = `${chapterId ?? ""}:${lines
    .map((line) => line.id ?? `${line.speaker}:${line.text}`)
    .join("|")}`;

  useEffect(() => {
    setCurrentIndex(0);
    setHistoryOpen(false);
    setArchiving(false);
  }, [dialogueKey, lines.length]);

  useEffect(
    () => () => {
      if (transitionTimer.current != null) {
        window.clearTimeout(transitionTimer.current);
      }
    },
    [],
  );

  const advance = () => {
    if (!completed && !archiving) {
      setArchiving(true);
      transitionTimer.current = window.setTimeout(() => {
        setCurrentIndex((index) => Math.min(lines.length - 1, index + 1));
        setArchiving(false);
        transitionTimer.current = null;
      }, 240);
      return;
    }
  };

  if (lines.length === 0) return null;
  const isPlayer =
    currentLine.speaker_id === "player" || currentLine.speaker === "玩家";
  const portraitAssetId = isPlayer
    ? undefined
    : currentLine.portrait_asset_id;

  return (
    <section aria-label={st("storyDialogue")}>
      <div className="mb-3 flex min-h-11 items-center justify-between gap-3">
        <p className="text-[13px] text-ink-soft" aria-live="polite">
          {st("dialogue", { current: currentIndex + 1, total: lines.length })}
        </p>
        {historyLines.length > 0 && (
          <button
            type="button"
            onClick={() => setHistoryOpen((open) => !open)}
            className="min-h-11 rounded-full border border-line bg-card px-4 text-[13px] font-medium text-sage-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage"
            aria-expanded={historyOpen}
            aria-controls="story-dialogue-history"
          >
            {historyOpen ? st("hideHistory") : st("showHistory")}
          </button>
        )}
      </div>

      {historyOpen && historyLines.length > 0 && (
        <div
          id="story-dialogue-history"
          role="log"
          aria-label={st("showHistory")}
          className="story-dialogue-history mb-4 max-h-72 space-y-3 overflow-y-auto rounded-2xl border border-line bg-paper-warm/70 p-3"
        >
          {historyLines.map((line, index) => (
            <DialogueBubble
              key={line.id ?? `${index}-${line.speaker}`}
              line={line}
            />
          ))}
        </div>
      )}

      <div
        className="relative touch-pan-y overflow-hidden rounded-3xl bg-paper-warm/45 p-3"
        onTouchStart={(event) => {
          touchStartY.current = event.changedTouches[0]?.clientY ?? null;
        }}
        onTouchEnd={(event) => {
          const endY = event.changedTouches[0]?.clientY;
          if (
            touchStartY.current != null &&
            endY != null &&
            touchStartY.current - endY > 44 &&
            historyLines.length > 0
          ) {
            setHistoryOpen(true);
          }
          touchStartY.current = null;
        }}
      >
        <div
          key={currentLine.id ?? `${currentIndex}-${currentLine.speaker}`}
          className={`story-dialogue-turn ${
            archiving ? "story-dialogue-turn--archiving" : ""
          } ${
            portraitAssetId
              ? "grid grid-cols-[4.75rem_minmax(0,1fr)] items-end gap-2"
              : ""
          }`}
          aria-live="polite"
        >
          {portraitAssetId && (
            <div
              className="self-end overflow-hidden"
              aria-label={`${currentLine.speaker}立绘`}
            >
              <StoryImage
                assetId={portraitAssetId}
                alt={`${currentLine.speaker}立绘`}
                eager
                className="rounded-none border-0 bg-transparent"
                imageClassName="object-contain object-bottom"
              />
            </div>
          )}
          <DialogueBubble
            line={currentLine}
            isCurrent
            onAdvance={!completed ? advance : undefined}
            className={portraitAssetId ? "!w-full" : ""}
          />
        </div>
      </div>

      {historyLines.length > 0 && !historyOpen && (
        <p className="mt-2 text-center text-[13px] text-ink-soft">
          {st("swipeHistory")}
        </p>
      )}

      {completed && onComplete && (
        <button
          type="button"
          onClick={onComplete}
          className="mt-4 min-h-12 w-full rounded-full bg-sage-deep px-5 text-base font-medium text-paper shadow-[var(--shadow-soft)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage"
        >
          {resolvedContinueLabel}
        </button>
      )}
    </section>
  );
}
