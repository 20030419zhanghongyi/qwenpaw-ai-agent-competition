import { useEffect, useRef } from "react";
import { useStoryMessages } from "../storyI18n";

interface SkipPuzzleDialogProps {
  open: boolean;
  message?: string;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function SkipPuzzleDialog({
  open,
  message,
  busy = false,
  onCancel,
  onConfirm,
}: SkipPuzzleDialogProps) {
  const st = useStoryMessages();
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    cancelRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onCancel();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, busy, onCancel]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[65] flex items-end justify-center bg-ink/45 px-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="story-skip-title"
    >
      <div
        className="w-full max-w-sm rounded-t-3xl border border-line bg-paper p-5 shadow-[var(--shadow-lift)] sm:rounded-3xl"
        style={{ paddingBottom: "max(1.25rem, env(safe-area-inset-bottom))" }}
      >
        <h2 id="story-skip-title" className="font-serif text-xl text-ink">
          {st("confirmSkipTitle")}
        </h2>
        <p className="mt-2 text-base leading-7 text-ink-soft">
          {message ?? st("skipDefaultBody")}
        </p>
        <div className="mt-5 grid grid-cols-2 gap-3">
          <button
            ref={cancelRef}
            type="button"
            disabled={busy}
            onClick={onCancel}
            className="min-h-12 rounded-full border border-line bg-card px-4 text-base text-ink disabled:opacity-45"
          >
            {st("keepSolving")}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onConfirm}
            className="min-h-12 rounded-full bg-clay px-4 text-base font-medium text-paper disabled:opacity-45"
          >
            {busy ? st("processing") : st("confirmSkip")}
          </button>
        </div>
      </div>
    </div>
  );
}
