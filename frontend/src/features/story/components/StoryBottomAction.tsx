import type { ReactNode } from "react";
import { useStoryMessages } from "../storyI18n";

interface StoryBottomActionProps {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  busy?: boolean;
  busyLabel?: string;
  secondary?: ReactNode;
  hint?: string;
  tone?: "primary" | "accent";
}

export function StoryBottomAction({
  label,
  onClick,
  disabled = false,
  busy = false,
  busyLabel,
  secondary,
  hint,
  tone = "primary",
}: StoryBottomActionProps) {
  const st = useStoryMessages();
  return (
    <div
      className="sticky bottom-0 z-20 border-t border-line/80 bg-paper/95 px-4 pt-3 backdrop-blur-md"
      style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
    >
      <div className="mx-auto max-w-[480px]">
        {hint && (
          <p className="mb-2 text-center text-[13px] leading-relaxed text-ink-soft">
            {hint}
          </p>
        )}
        <div className={secondary ? "grid grid-cols-[1fr_2fr] gap-2" : ""}>
          {secondary}
          <button
            type="button"
            disabled={disabled || busy}
            onClick={onClick}
            aria-busy={busy}
            className={`min-h-12 w-full rounded-full px-5 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-45 ${
              tone === "accent" ? "bg-ochre" : "bg-sage-deep"
            }`}
          >
            {busy ? (busyLabel ?? st("processing")) : label}
          </button>
        </div>
      </div>
    </div>
  );
}
