import { useState } from "react";
import { deletePostcard, postcardImageSrc, PostcardApiError } from "@/api/postcards";
import { t } from "@/i18n";
import type { LanguageCode } from "@/types";
import type { Postcard } from "@/types/postcards";

export function PostcardActions({
  postcard,
  language,
  onDeleted,
  onRegenerate,
}: {
  postcard: Postcard;
  language: LanguageCode;
  onDeleted?: () => void;
  onRegenerate?: () => void;
}) {
  const [shareNote, setShareNote] = useState<string | null>(null);
  const [busy, setBusy] = useState<"delete" | "regenerate" | null>(null);
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

  async function handleDelete() {
    if (!window.confirm(t(language, "postcardDeleteConfirm"))) return;
    setBusy("delete");
    setShareNote(null);
    try {
      await deletePostcard(postcard.postcard_id);
      onDeleted?.();
    } catch (err) {
      const message =
        err instanceof PostcardApiError || err instanceof Error ? err.message : "";
      setShareNote(message || t(language, "postcardDeleteError"));
      setBusy(null);
    }
  }

  async function handleRegenerate() {
    if (!window.confirm(t(language, "postcardRegenerateConfirm"))) return;
    setBusy("regenerate");
    setShareNote(null);
    try {
      await deletePostcard(postcard.postcard_id);
      onRegenerate?.();
    } catch (err) {
      const message =
        err instanceof PostcardApiError || err instanceof Error ? err.message : "";
      setShareNote(message || t(language, "postcardDeleteError"));
      setBusy(null);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={() => void handleDownload()}
          disabled={busy !== null}
          className="h-11 flex-1 rounded-full border border-line bg-card text-sm font-medium text-ink transition hover:border-sage disabled:opacity-50"
        >
          {t(language, "postcardDownload")}
        </button>
        <button
          type="button"
          onClick={() => void handleShare()}
          disabled={busy !== null}
          className="h-11 flex-1 rounded-full bg-sage-deep text-sm font-medium text-paper transition hover:bg-moss disabled:opacity-50"
        >
          {t(language, "postcardShare")}
        </button>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={() => void handleRegenerate()}
          disabled={busy !== null}
          className="h-11 flex-1 rounded-full border border-sage-deep text-sm font-medium text-sage-deep transition hover:bg-sage-deep/10 disabled:opacity-50"
        >
          {busy === "regenerate"
            ? t(language, "postcardDeleting")
            : t(language, "postcardRegenerate")}
        </button>
        <button
          type="button"
          onClick={() => void handleDelete()}
          disabled={busy !== null}
          className="h-11 flex-1 rounded-full border border-line text-sm font-medium text-ink-soft transition hover:border-clay hover:text-clay disabled:opacity-50"
        >
          {busy === "delete"
            ? t(language, "postcardDeleting")
            : t(language, "postcardDelete")}
        </button>
      </div>
      {shareNote ? <p className="text-center text-xs text-ink-soft">{shareNote}</p> : null}
    </div>
  );
}
