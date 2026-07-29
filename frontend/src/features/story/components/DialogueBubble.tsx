import type { StoryDialogueLine } from "../types";

interface DialogueBubbleProps {
  line: StoryDialogueLine;
  isCurrent?: boolean;
  isPlayer?: boolean;
  onAdvance?: () => void;
  className?: string;
}

export function DialogueBubble({
  line,
  isCurrent = false,
  isPlayer = line.speaker_id === "player" || line.speaker === "玩家",
  onAdvance,
  className = "",
}: DialogueBubbleProps) {
  const content = (
    <>
      <p
        className={`text-[13px] font-semibold ${
          isPlayer ? "text-ochre" : "text-sage-deep"
        }`}
      >
        {isPlayer ? "你" : line.speaker}
      </p>
      <p className="mt-1 text-base leading-7 text-ink">{line.text}</p>
      {isCurrent && onAdvance && (
        <span className="mt-2 block text-right text-[13px] text-ink-soft">
          轻触继续 <span aria-hidden>→</span>
        </span>
      )}
    </>
  );

  const classes = `w-[88%] rounded-2xl border p-4 text-left shadow-[var(--shadow-soft)] ${
    isPlayer
      ? "ml-auto border-ochre/25 bg-ochre/5"
      : "mr-auto border-line bg-card"
  } ${isCurrent ? "opacity-100" : "opacity-75"} ${className}`;

  return isCurrent && onAdvance ? (
    <button
      type="button"
      onClick={onAdvance}
      data-story-dialogue-bubble="current"
      className={`${classes} min-h-11 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage`}
      aria-label={`${isPlayer ? "你" : line.speaker}说：${line.text}。轻触继续`}
    >
      {content}
    </button>
  ) : (
    <div
      data-story-dialogue-bubble={isCurrent ? "current" : "history"}
      className={classes}
    >
      {content}
    </div>
  );
}
