import { useEffect, useRef, useState } from "react";
import { createPostcard, PostcardApiError } from "@/api/postcards";
import { ErrorState, LoadingState } from "@/components/common/States";
import { t } from "@/i18n";
import type { LanguageCode } from "@/types";
import type { Postcard } from "@/types/postcards";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_SIZE = 8 * 1024 * 1024;

type Phase = "idle" | "creating" | "done" | "error";

export function PostcardCreateForm({
  tripId,
  poiId,
  poiName,
  language,
  onCreated,
  onSkip,
}: {
  tripId: string;
  poiId: string;
  poiName?: string;
  language: LanguageCode;
  onCreated: (postcard: Postcard) => void;
  onSkip?: () => void;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function validate(candidate: File): string | null {
    if (!ALLOWED_TYPES.includes(candidate.type)) {
      return t(language, "postcardPhotoInvalid");
    }
    if (candidate.size > MAX_SIZE) {
      return t(language, "postcardPhotoTooLarge");
    }
    return null;
  }

  function handlePick(candidate: File | null) {
    setError(null);
    if (!candidate) return;
    const validation = validate(candidate);
    if (validation) {
      setError(validation);
      setFile(null);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(candidate));
    setFile(candidate);
    setPhase("idle");
  }

  async function handleCreate() {
    if (!file) {
      setError(t(language, "postcardNeedPhoto"));
      return;
    }
    setPhase("creating");
    setError(null);
    try {
      const postcard = await createPostcard({
        tripId,
        poiId,
        photo: file,
        language,
      });
      setPhase("done");
      onCreated(postcard);
    } catch (err) {
      const message =
        err instanceof PostcardApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "";
      setError(
        message.includes("Failed to fetch")
          ? t(language, "backendDown")
          : message.includes("checked in")
            ? t(language, "postcardNeedCheckin")
            : message || t(language, "postcardCreateError"),
      );
      setPhase("error");
    }
  }

  if (phase === "creating") {
    return <LoadingState label={t(language, "postcardCreating")} />;
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
          {t(language, "postcardCreateEyebrow")}
        </p>
        <h2 className="mt-1 font-display text-2xl text-ink">
          {poiName || t(language, "postcardCreateTitle")}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          {t(language, "postcardCreateLead")}
        </p>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        className="hidden"
        onChange={(e) => handlePick(e.target.files?.[0] ?? null)}
      />

      {previewUrl ? (
        <div className="overflow-hidden rounded-2xl border border-line bg-paper-warm">
          <img
            src={previewUrl}
            alt={t(language, "postcardPreviewAlt")}
            className="aspect-[4/3] w-full object-cover"
          />
        </div>
      ) : (
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="flex aspect-[4/3] w-full flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-sage-deep/40 bg-paper-warm/60 text-ink-soft transition hover:border-sage-deep hover:bg-paper-warm"
        >
          <span className="font-serif text-2xl text-sage-deep">◎</span>
          <span className="text-sm">{t(language, "postcardPickPhoto")}</span>
          <span className="px-6 text-center text-xs">{t(language, "postcardPrivacyNote")}</span>
        </button>
      )}

      {error ? (
        <ErrorState
          title={t(language, "errorTitle")}
          message={error}
          onRetry={phase === "error" && file ? () => void handleCreate() : undefined}
          retryLabel={t(language, "retry")}
        />
      ) : null}

      <div className="flex flex-col gap-3 sm:flex-row">
        {previewUrl ? (
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="h-12 rounded-full border border-line bg-card px-5 text-sm text-ink transition hover:border-sage"
          >
            {t(language, "postcardChangePhoto")}
          </button>
        ) : null}
        <button
          type="button"
          disabled={!file}
          onClick={() => void handleCreate()}
          className="h-12 flex-1 rounded-full bg-sage-deep px-5 text-sm font-medium text-paper transition hover:bg-moss disabled:opacity-50"
        >
          {t(language, "postcardGenerate")}
        </button>
        {onSkip ? (
          <button
            type="button"
            onClick={onSkip}
            className="h-12 rounded-full px-5 text-sm text-ink-soft transition hover:text-ink"
          >
            {t(language, "postcardSkip")}
          </button>
        ) : null}
      </div>
    </div>
  );
}
