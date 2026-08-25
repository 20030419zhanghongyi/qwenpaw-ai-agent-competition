import type { StoryNodeOverview, StoryReward } from "@/types/stories";
import { useStoryMessages } from "../storyI18n";

interface ChapterRecapDialogProps {
  node: StoryNodeOverview | null;
  poiName?: string;
  reward?: StoryReward;
  skipped?: boolean;
  onClose: () => void;
}

export function ChapterRecapDialog({
  node,
  poiName,
  reward,
  skipped = false,
  onClose,
}: ChapterRecapDialogProps) {
  const st = useStoryMessages();
  if (!node) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="chapter-recap-title"
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink/35 px-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:items-center"
      onClick={onClose}
    >
      <section
        className="w-full max-w-[480px] rounded-3xl border border-line bg-paper p-5 shadow-[var(--shadow-lift)]"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-ochre">
              {st("chapterRecap")}{node.story_time ? ` · ${node.story_time}` : ""}
            </p>
            <h2
              id="chapter-recap-title"
              className="mt-1 font-serif text-xl font-semibold"
            >
              {node.title}
            </h2>
            {poiName && (
              <p className="mt-1 text-sm text-sage-deep">{poiName}</p>
            )}
          </div>
          <span className="shrink-0 rounded-full border border-line bg-card px-3 py-1 text-xs text-ink-soft">
            {skipped ? st("puzzleSkipped") : st("chapterDone")}
          </span>
        </div>

        {reward ? (
          <div className="mt-4 rounded-2xl border border-ochre/25 bg-ochre/5 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ochre">
              {st("stationNote")}
            </p>
            <p className="mt-1 text-base font-medium text-ink">
              {reward.name ?? reward.id}
            </p>
            {reward.text && (
              <p className="mt-2 text-base leading-7 text-ink-soft">
                {reward.text}
              </p>
            )}
          </div>
        ) : (
          <p className="mt-4 text-base leading-7 text-ink-soft">
            {skipped
              ? st("skippedRecapBody")
              : st("completedRecapBody")}
          </p>
        )}

        <p className="mt-3 text-sm leading-6 text-ink-soft">
          {st("recapIntegrity")}
        </p>
        <button
          type="button"
          onClick={onClose}
          className="mt-5 min-h-12 w-full rounded-full bg-sage-deep px-5 text-base font-medium text-paper"
        >
          {st("closeRecap")}
        </button>
      </section>
    </div>
  );
}
