import { useEffect, useRef, useState } from "react";
import { recognizeGuidePhoto, type GuidePhotoResponse } from "@/api/client";
import { ErrorState, LoadingState } from "@/components/common/States";
import { t } from "@/i18n";
import type { LanguageCode } from "@/types";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_SIZE = 8 * 1024 * 1024; // 8 MB

interface PhotoRecognitionPanelProps {
  language: LanguageCode;
  onRecognized?: (poiName: string) => void;
  onManualSelect?: () => void;
}

type Phase = "idle" | "uploading" | "success" | "error";

export function PhotoRecognitionPanel({
  language,
  onRecognized,
  onManualSelect,
}: PhotoRecognitionPanelProps) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result, setResult] = useState<GuidePhotoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const isHighConfidence =
    result?.candidate_poi && (result.confidence ?? 0) >= 0.6;

  function validateFile(file: File): string | null {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return t(language, "guidePhotoError");
    }
    if (file.size > MAX_SIZE) {
      return t(language, "guidePhotoError");
    }
    return null;
  }

  function handleFilePicked(file: File | null) {
    setValidationError(null);
    setError(null);
    setResult(null);

    if (!file) return;

    const validation = validateFile(file);
    if (validation) {
      setValidationError(validation);
      return;
    }

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setPhase("uploading");
    void (async () => {
      try {
        const res = await recognizeGuidePhoto({ file, language });
        setResult(res);
        setPhase("success");
        if (res.candidate_poi && (res.confidence ?? 0) >= 0.6 && onRecognized) {
          onRecognized(res.candidate_poi);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "";
        setError(
          message.includes("Failed to fetch")
            ? t(language, "backendDown")
            : t(language, "guidePhotoError"),
        );
        setPhase("error");
      }
    })();
  }

  function handleRetry() {
    if (fileRef.current?.files?.[0]) {
      handleFilePicked(fileRef.current.files[0]);
    } else {
      setPhase("idle");
      setPreviewUrl(null);
      setResult(null);
      setError(null);
    }
  }

  function handleReset() {
    setPhase("idle");
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    setValidationError(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  return (
    <div className="rounded-[1.75rem] border border-sage-deep/20 bg-moss shadow-[var(--shadow-soft)] overflow-hidden">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3 border-b border-paper/10 bg-moss/95 px-5 py-4">
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"
          className="hidden"
          onChange={(e) => handleFilePicked(e.target.files?.[0] ?? null)}
        />
        <button
          type="button"
          disabled={phase === "uploading"}
          onClick={() => fileRef.current?.click()}
          className="rounded-full bg-paper px-5 py-2.5 text-sm font-medium text-moss transition hover:bg-paper-warm disabled:opacity-60"
        >
          {phase === "uploading"
            ? t(language, "guidePhotoUploading")
            : t(language, "guidePhotoUpload")}
        </button>
        <p className="text-xs text-paper/75">{t(language, "guidePhotoHint")}</p>
      </div>

      {/* Body */}
      <div className="p-5 sm:p-6">
        {/* Validation error */}
        {validationError ? (
          <ErrorState
            message={validationError}
            onRetry={handleReset}
            retryLabel={t(language, "guidePhotoUpload")}
          />
        ) : null}

        {/* Uploading */}
        {phase === "uploading" ? (
          <LoadingState label={t(language, "guidePhotoUploading")} />
        ) : null}

        {/* Error */}
        {phase === "error" && error ? (
          <ErrorState
            message={error}
            onRetry={handleRetry}
            retryLabel={t(language, "retry")}
          />
        ) : null}

        {/* Success: high confidence */}
        {phase === "success" && isHighConfidence ? (
          <div className="space-y-4">
            {previewUrl ? (
              <div className="overflow-hidden rounded-2xl">
                <img
                  src={previewUrl}
                  alt={t(language, "guidePhotoYourShot")}
                  className="aspect-[4/3] w-full object-cover"
                />
              </div>
            ) : null}
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-paper/70">
              {t(language, "guidePhotoYourShot")}
            </p>
            <div className="rounded-2xl border border-paper/20 bg-paper/10 px-4 py-3">
              <p className="text-sm text-paper">
                {t(language, "guidePhotoRecognized")}
                <span className="font-display text-base">{result!.candidate_poi}</span>
                {result!.confidence != null
                  ? ` · ${Math.round(result!.confidence * 100)}%`
                  : ""}
              </p>
            </div>
            {result!.explanation?.text ? (
              <p className="text-sm leading-relaxed text-paper/85 whitespace-pre-wrap">
                {result!.explanation.text}
              </p>
            ) : null}
          </div>
        ) : null}

        {/* Success: low confidence */}
        {phase === "success" && !isHighConfidence ? (
          <div className="space-y-4">
            {previewUrl ? (
              <div className="overflow-hidden rounded-2xl">
                <img
                  src={previewUrl}
                  alt={t(language, "guidePhotoYourShot")}
                  className="aspect-[4/3] w-full object-cover"
                />
              </div>
            ) : null}
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-paper/70">
              {t(language, "guidePhotoYourShot")}
            </p>
            <div className="rounded-2xl border border-paper/20 bg-paper/10 px-4 py-3">
              <p className="text-sm text-paper">
                {result!.low_confidence_hint || result!.error || t(language, "guidePhotoUncertain")}
              </p>
            </div>
            {result!.description ? (
              <p className="text-sm leading-relaxed text-paper/75">
                {t(language, "guidePhotoSeen")}
                {result!.description}
              </p>
            ) : null}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleReset}
                className="rounded-full border border-paper/30 bg-transparent px-4 py-2 text-sm text-paper transition hover:bg-paper/10"
              >
                {t(language, "guidePhotoUpload")}
              </button>
              {onManualSelect ? (
                <button
                  type="button"
                  onClick={onManualSelect}
                  className="rounded-full bg-paper px-4 py-2 text-sm font-medium text-moss transition hover:bg-paper-warm"
                >
                  {t(language, "guidePickAnother")}
                </button>
              ) : null}
            </div>
          </div>
        ) : null}

        {/* Idle */}
        {phase === "idle" ? (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <div
              aria-hidden
              className="grid size-14 place-items-center rounded-2xl bg-paper/10 font-serif text-2xl text-paper/50"
            >
              📷
            </div>
            <p className="text-sm text-paper/60">{t(language, "guidePhotoHint")}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
