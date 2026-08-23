import { useRef, useState } from "react";
import { StoryImage } from "../assets";
import type { StoryAssetRef } from "@/types/stories";
import { useStoryMessages } from "../storyI18n";

interface StoryComicReaderProps {
  comics: StoryAssetRef[];
  index: number;
  onIndexChange: (index: number) => void;
  onComplete: () => void;
  onOpen: (comic: StoryAssetRef) => void;
}

export function StoryComicReader({
  comics,
  index,
  onIndexChange,
  onComplete,
  onOpen,
}: StoryComicReaderProps) {
  const st = useStoryMessages();
  const touchStartX = useRef<number | null>(null);
  const [direction, setDirection] = useState<"forward" | "backward">("forward");
  const currentComic = comics[index];

  if (!currentComic) return null;

  const goTo = (nextIndex: number) => {
    if (nextIndex === index) return;
    setDirection(nextIndex < index ? "backward" : "forward");
    onIndexChange(nextIndex);
  };
  const previous = () => goTo(Math.max(0, index - 1));
  const next = () => {
    if (index < comics.length - 1) {
      goTo(index + 1);
    } else {
      onComplete();
    }
  };

  return (
    <section
      className="mt-4"
      aria-label={st("scene")}
      onTouchStart={(event) => {
        touchStartX.current = event.changedTouches[0]?.clientX ?? null;
      }}
      onTouchEnd={(event) => {
        const endX = event.changedTouches[0]?.clientX;
        if (touchStartX.current == null || endX == null) return;
        const distance = endX - touchStartX.current;
        if (distance > 52 && index > 0) previous();
        if (distance < -52) next();
        touchStartX.current = null;
      }}
    >
      <div
        key={currentComic.asset_id}
        className={`story-comic-page story-comic-page--${direction}`}
        data-comic-direction={direction}
      >
        <StoryImage
          assetId={currentComic.asset_id}
          alt={currentComic.alt}
          eager={index === 0}
          onOpen={() => onOpen(currentComic)}
        />
        <p className="mt-2 text-base leading-7 text-ink-soft">
          {currentComic.caption}
        </p>
      </div>

      <div className="mt-3 grid grid-cols-[auto_1fr_auto] items-center gap-2">
        <button
          type="button"
          onClick={previous}
          disabled={index === 0}
          className="min-h-11 rounded-full border border-line bg-card px-4 text-sm font-medium text-sage-deep disabled:cursor-not-allowed disabled:opacity-35"
        >
          {st("previousPanel")}
        </button>
        <div className="flex justify-center" aria-label={st("dialogue", { current: index + 1, total: comics.length })}>
          {comics.map((comic, pageIndex) => (
            <button
              key={comic.asset_id}
              type="button"
              onClick={() => goTo(pageIndex)}
              className="grid size-11 place-items-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage"
              aria-label={`${st("scene")} ${pageIndex + 1}`}
              aria-current={pageIndex === index ? "step" : undefined}
            >
              <span
                className={`block size-2.5 rounded-full ${
                  pageIndex === index ? "bg-sage-deep" : "bg-line"
                }`}
                aria-hidden
              />
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={next}
          className="min-h-11 rounded-full bg-sage-deep px-4 text-sm font-medium text-paper"
        >
          {index < comics.length - 1 ? st("nextPanel") : st("enterDialogue")}
        </button>
      </div>
      {comics.length > 1 && (
        <p className="mt-1 text-center text-[13px] text-ink-soft">
          {index + 1}/{comics.length} · {st("swipePages")}
        </p>
      )}
    </section>
  );
}
