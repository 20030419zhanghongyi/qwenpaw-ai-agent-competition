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
  if (assetId.startsWith("V4-CHAR-")) {
    return "/story/v4/_placeholder-portrait.svg";
  }
  if (PETAL_ASSET_IDS.has(assetId)) {
    return "/story/v4/_placeholder-petal.svg";
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
  const isInteractive = Boolean(onOpen && item);
  const showFallbackLabel =
    failed &&
    item &&
    !assetId.startsWith("V4-CHAR-") &&
    !PETAL_ASSET_IDS.has(assetId);
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
        <span className="flex size-full flex-col items-center justify-center gap-2 bg-[radial-gradient(circle_at_center,var(--color-line)_1px,transparent_1px)] bg-[length:14px_14px] px-5 text-center text-sm text-ink-soft">
          <span aria-hidden className="text-2xl opacity-60">◇</span>
          <span>{label}</span>
          {import.meta.env.DEV && (
            <span className="font-mono text-[11px] text-ink-soft/70">
              {assetId}
            </span>
          )}
        </span>
      )}
      {showFallbackLabel && (
        <span className="pointer-events-none absolute inset-x-3 bottom-3 rounded-xl border border-paper/70 bg-ink/70 px-3 py-2 text-center text-[13px] leading-5 text-paper">
          {label}
          {import.meta.env.DEV && (
            <span className="ml-1 font-mono text-[11px] text-paper/70">
              · {assetId}
            </span>
          )}
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
