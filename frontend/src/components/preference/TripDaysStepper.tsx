import { t } from "@/i18n";
import {
  clampTripDays,
  TRIP_DAYS_MAX,
  TRIP_DAYS_MIN,
} from "@/lib/preference";
import type { LanguageCode } from "@/types";

export function TripDaysStepper({
  language,
  value,
  disabled,
  highlighted,
  onChange,
}: {
  language: LanguageCode;
  value: number;
  disabled?: boolean;
  highlighted?: boolean;
  onChange: (next: number) => void;
}) {
  const days = clampTripDays(value);
  const label = t(language, "tripDaysPlay").replace("{n}", String(days));

  return (
    <div
      className={[
        "mt-3 flex items-center justify-between gap-3 rounded-2xl border px-4 py-3",
        highlighted
          ? "border-sage-deep bg-sage-deep/5 ring-2 ring-ochre ring-offset-2 ring-offset-paper"
          : "border-line bg-card",
      ].join(" ")}
    >
      <p className="text-sm font-medium text-ink">{label}</p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={disabled || days <= TRIP_DAYS_MIN}
          aria-label={t(language, "tripDaysMinus")}
          onClick={() => onChange(clampTripDays(days - 1))}
          className="flex h-9 w-9 items-center justify-center rounded-full border border-line text-lg text-ink transition hover:border-sage disabled:cursor-not-allowed disabled:opacity-40"
        >
          −
        </button>
        <span className="min-w-[1.5rem] text-center font-display text-xl text-sage-deep">
          {days}
        </span>
        <button
          type="button"
          disabled={disabled || days >= TRIP_DAYS_MAX}
          aria-label={t(language, "tripDaysPlus")}
          onClick={() => onChange(clampTripDays(days + 1))}
          className="flex h-9 w-9 items-center justify-center rounded-full border border-line text-lg text-ink transition hover:border-sage disabled:cursor-not-allowed disabled:opacity-40"
        >
          +
        </button>
      </div>
    </div>
  );
}
