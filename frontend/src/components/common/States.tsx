export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-soft">
      <div
        className="size-8 animate-spin rounded-full border-2 border-line border-t-sage-deep"
        aria-hidden
      />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function ErrorState({
  title = "Error",
  message,
  onRetry,
  retryLabel = "Retry",
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
}) {
  return (
    <div className="rounded-2xl border border-line bg-card px-5 py-6 text-center">
      <p className="font-display text-lg text-ink">{title}</p>
      <p className="mt-2 text-sm leading-relaxed text-ink-soft">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-5 rounded-full bg-sage-deep px-6 py-2.5 text-sm font-medium text-paper hover:bg-moss"
        >
          {retryLabel}
        </button>
      ) : null}
    </div>
  );
}
