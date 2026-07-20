import { useState } from "react";
import { postcardImageSrc } from "@/api/postcards";
import { t } from "@/i18n";
import type { LanguageCode } from "@/types";
import type { Postcard } from "@/types/postcards";

export function PostcardActions({
  postcard,
  language,
}: {
  postcard: Postcard;
  language: LanguageCode;
}) {
  const [shareNote, setShareNote] = useState<string | null>(null);
  const src = postcardImageSrc(postcard.image_url);

  async function handleDownload() {
    setShareNote(null);
    try {
      const response = await fetch(src);
      if (!response.ok) throw new Error("download failed");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `macau-postcard-${postcard.poi_id}.svg`;
      anchor.click();
      URL.revokeObjectURL(url);
      setShareNote(t(language, "postcardDownloaded"));
    } catch {
      setShareNote(t(language, "postcardDownloadError"));
    }
  }

  async function handleShare() {
    setShareNote(null);
    const shareUrl = `${window.location.origin}/postcards/${encodeURIComponent(postcard.postcard_id)}?trip=${encodeURIComponent(postcard.trip_id)}`;
    try {
      if (navigator.share) {
        await navigator.share({
          title: `${postcard.poi_name} · Macau StoryWalk`,
          text: postcard.caption,
          url: shareUrl,
        });
        return;
      }
      await navigator.clipboard.writeText(shareUrl);
      setShareNote(t(language, "postcardLinkCopied"));
    } catch {
      setShareNote(t(language, "postcardShareError"));
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={() => void handleDownload()}
          className="h-11 flex-1 rounded-full border border-line bg-card text-sm font-medium text-ink transition hover:border-sage"
        >
          {t(language, "postcardDownload")}
        </button>
        <button
          type="button"
          onClick={() => void handleShare()}
          className="h-11 flex-1 rounded-full bg-sage-deep text-sm font-medium text-paper transition hover:bg-moss"
        >
          {t(language, "postcardShare")}
        </button>
      </div>
      {shareNote ? <p className="text-center text-xs text-ink-soft">{shareNote}</p> : null}
    </div>
  );
}
