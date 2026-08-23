import { useEffect, useState, type CSSProperties } from "react";
import { resolveStoryAsset } from "./storyAssetManifest";

const PETAL_ASSET_IDS = new Set([
  "V4-AMA-05",
  "V4-MAN-06",
  "V4-SEN-05",
  "V4-SAM-06",
  "V4-LOU-05",
]);

function placeholderImage(assetId: string): string {
  if (PETAL_ASSET_IDS.has(assetId)) {
    return "/story/v4/_placeholder-petal.svg";
  }
  if (assetId.startsWith("V4-CHAR-")) {
    return "/story/v4/_placeholder-portrait.svg";
  }
  return "/story/v4/_placeholder.svg";
}

interface StoryImageProps {
  assetId: string;
  alt?: string;
  className?: string;
  imageClassName?: string;
  eager?: boolean;
  onOpen?: (assetId: string) => void;
}

export function StoryImage({
  assetId,
  alt,
  className = "",
  imageClassName = "",
  eager = false,
  onOpen,
}: StoryImageProps) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [assetId]);

  const item = resolveStoryAsset(assetId);
  const ratio = item?.aspectRatio ?? "4/5";
  const label = alt ?? item?.fallbackLabel ?? "故事图片";
  const fallbackLabel = item?.fallbackLabel ?? "图片素材";
  const isInteractive = Boolean(onOpen && item);
  const showFallbackLabel = failed && item;
  const Wrapper = isInteractive ? "button" : "div";

  return (
    <Wrapper
      {...(isInteractive
        ? {
            type: "button" as const,
            onClick: () => onOpen?.(assetId),
            "aria-label": `查看大图：${label}`,
          }
        : {})}
      className={`relative block w-full overflow-hidden rounded-2xl border border-line bg-paper-warm text-left ${className}`}
      style={{ aspectRatio: ratio } as CSSProperties}
    >
      {item ? (
        <img
          src={failed ? placeholderImage(assetId) : item.src}
          alt={label}
          loading={eager ? "eager" : "lazy"}
          decoding="async"
          onError={() => {
            if (!failed) setFailed(true);
          }}
          className={`size-full object-cover ${imageClassName}`}
          style={{ objectPosition: item.objectPosition }}
        />
      ) : (
        <span className="flex size-full flex-col items-center justify-center bg-[url('/story/v4/_placeholder.svg')] bg-cover px-5 text-center text-sm text-ink-soft">
          <span>
            {import.meta.env.DEV ? "未登记的图片素材" : "图片素材暂未提供"}
          </span>
          {import.meta.env.DEV ? (
            <span className="mt-1 font-mono text-[11px] text-ink-soft/70">
              {assetId}
            </span>
          ) : null}
        </span>
      )}
      {showFallbackLabel && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-x-2 bottom-2 rounded-lg border border-paper/70 bg-ink/75 px-2 py-1.5 text-center text-[11px] leading-4 text-paper"
        >
          <span className="block">
            {import.meta.env.DEV
              ? fallbackLabel
              : `${fallbackLabel}暂未提供`}
          </span>
          {import.meta.env.DEV ? (
            <span className="block font-mono text-[10px] text-paper/75">
              {assetId}
            </span>
          ) : null}
        </span>
      )}
      {item?.creditLabel && !failed && (
        <span className="pointer-events-none absolute bottom-2 left-2 rounded-md bg-ink/75 px-2 py-1 text-[10px] leading-4 text-paper shadow-[var(--shadow-soft)]">
          {item.creditLabel}
        </span>
      )}
      {isInteractive && (
        <span className="absolute right-3 top-3 grid size-11 place-items-center rounded-full border border-paper/70 bg-ink/65 text-paper shadow-[var(--shadow-soft)]">
          <span aria-hidden>⌕</span>
          <span className="sr-only">查看大图</span>
        </span>
      )}
    </Wrapper>
  );
}
