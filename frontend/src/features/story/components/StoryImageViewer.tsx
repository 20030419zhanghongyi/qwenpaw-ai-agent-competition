import { useEffect, useRef } from "react";
import { useWalk } from "@/state/WalkContext";
import { StoryImage } from "../assets";
import { resolveStoryAsset } from "../assets/storyAssetManifest";
import { useStoryMessages } from "../storyI18n";

interface StoryImageViewerProps {
  assetId: string | null;
  alt?: string;
  caption?: string;
  onClose: () => void;
}

export function StoryImageViewer({
  assetId,
  alt,
  caption,
  onClose,
}: StoryImageViewerProps) {
  const st = useStoryMessages();
  const { language } = useWalk();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!assetId) return;
    const marker = `story-image-viewer-${assetId}-${Date.now()}`;
    let closedByHistory = false;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.history.pushState(
      { ...window.history.state, storyImageViewer: marker },
      "",
    );
    closeRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    const handlePopState = () => {
      closedByHistory = true;
      onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("popstate", handlePopState);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("popstate", handlePopState);
      if (
        !closedByHistory &&
        window.history.state?.storyImageViewer === marker
      ) {
        window.history.back();
      }
    };
  }, [assetId, onClose]);

  if (!assetId) return null;
  const item = resolveStoryAsset(assetId, language);
  const label = alt ?? item?.fallbackLabel ?? st("storyImage");

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={st("largeImageNamed", { label })}
      className="fixed inset-0 z-[70] flex flex-col bg-ink/95"
      onClick={onClose}
    >
      <div
        className="flex items-center justify-between px-4 text-paper"
        style={{ paddingTop: "max(1rem, env(safe-area-inset-top))" }}
      >
        <p className="pr-4 text-sm">{label}</p>
        <button
          ref={closeRef}
          type="button"
          onClick={onClose}
          className="grid size-11 shrink-0 place-items-center rounded-full border border-paper/20 bg-paper/10 text-xl"
          aria-label={st("closeLargeImage")}
        >
          ×
        </button>
      </div>
      <div
        className="flex min-h-0 flex-1 items-center justify-center overflow-auto p-4"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="w-full max-w-lg touch-pinch-zoom">
          <StoryImage
            assetId={assetId}
            alt={label}
            eager
            className="max-h-[78dvh] border-paper/15 bg-ink"
            imageClassName="object-contain"
          />
          {caption && (
            <p className="mx-auto mt-3 max-w-md text-center text-sm leading-relaxed text-paper/75">
              {caption}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
