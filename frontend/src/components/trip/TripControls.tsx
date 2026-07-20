import { useEffect } from "react";
import { Link } from "react-router-dom";
import { t } from "@/i18n";
import { useTrip } from "@/state/TripContext";
import { useWalk } from "@/state/WalkContext";

export interface TripControlsProps {
  userId: string;
  routeId: string;
  currentPoiId?: string;
  /** Ordered POI ids from the current walk (may differ from template). */
  stopPoiIds?: string[];
}

function displayTripError(language: Parameters<typeof t>[0], error: string): string {
  if (error === "TRIP_BACKEND_STALE") {
    return t(language, "tripBackendStale");
  }
  if (error === "TRIP_POI_MISMATCH" || /not part of trip/i.test(error)) {
    return t(language, "tripPoiMismatch");
  }
  return error;
}

export function TripControls({
  userId,
  routeId,
  currentPoiId,
  stopPoiIds,
}: TripControlsProps) {
  const { language } = useWalk();
  const {
    trip,
    progress,
    loading,
    error,
    startTrip,
    loadCurrentTrip,
    simulateArrive,
  } = useTrip();

  useEffect(() => {
    if (!userId) return;
    void loadCurrentTrip(userId).catch(() => {
      // The context exposes non-404 failures for display.
    });
  }, [loadCurrentTrip, userId]);

  const isCurrentRoute = trip?.route_id === routeId;
  const isCompleted = isCurrentRoute && trip?.status === "completed";
  const currentPoiChecked =
    Boolean(currentPoiId) &&
    Boolean(trip?.checked_in_poi_ids.includes(currentPoiId ?? ""));
  const currentPoiBelongsToTrip =
    Boolean(currentPoiId) &&
    Boolean(trip?.stop_poi_ids.includes(currentPoiId ?? ""));

  const handleStart = async () => {
    try {
      await startTrip(userId, routeId, stopPoiIds);
    } catch {
      // The context exposes the backend error for display.
    }
  };

  const handleSimulateArrive = async () => {
    if (!currentPoiId) return;
    try {
      await simulateArrive(userId, routeId, currentPoiId, stopPoiIds);
    } catch {
      // The context exposes the backend error for display.
    }
  };

  const postcardHref =
    isCurrentRoute && trip && currentPoiId && currentPoiChecked
      ? `/postcards/new?trip=${encodeURIComponent(trip.trip_id)}&poi=${encodeURIComponent(currentPoiId)}`
      : isCurrentRoute && trip
        ? `/postcards?trip=${encodeURIComponent(trip.trip_id)}`
        : "/postcards";

  return (
    <section className="rounded-2xl border border-line bg-card p-4 shadow-[var(--shadow-soft)]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-sage-deep">
            {t(language, "tripProgress")}
          </p>
          {isCurrentRoute && progress ? (
            <p className="mt-1 text-sm text-ink">
              {t(language, "tripCompletedStops")
                .replace("{done}", String(progress.completed_stops))
                .replace("{total}", String(progress.total_stops))}
            </p>
          ) : (
            <p className="mt-1 text-sm text-ink-soft">{t(language, "tripNotStarted")}</p>
          )}
        </div>
        {isCurrentRoute && progress ? (
          <span className="text-sm font-medium text-sage-deep">
            {Math.round(progress.completion_ratio * 100)}%
          </span>
        ) : null}
      </div>

      {isCurrentRoute && progress ? (
        <div
          className="mt-3 h-2 overflow-hidden rounded-full bg-paper-warm"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={progress.total_stops}
          aria-valuenow={progress.completed_stops}
        >
          <div
            className="h-full rounded-full bg-sage-deep transition-[width]"
            style={{ width: `${Math.round(progress.completion_ratio * 100)}%` }}
          />
        </div>
      ) : null}

      <p className="mt-3 text-[11px] leading-relaxed text-ink-soft">
        {t(language, "tripDemoHint")}
      </p>

      {error ? (
        <p role="alert" className="mt-3 text-sm text-clay">
          {displayTripError(language, error)}
        </p>
      ) : null}

      <div className="mt-4 space-y-2">
        {!isCurrentRoute ? (
          <>
            {trip?.status === "active" ? (
              <p className="mb-2 text-xs text-ink-soft">{t(language, "tripOtherActive")}</p>
            ) : null}
            <button
              type="button"
              disabled={loading || !userId || !routeId || !currentPoiId}
              onClick={() => void handleSimulateArrive()}
              className="h-11 w-full rounded-full bg-sage-deep text-sm font-medium text-paper hover:bg-moss disabled:opacity-60"
            >
              {loading ? t(language, "tripBusy") : t(language, "tripSimulateArrive")}
            </button>
            <button
              type="button"
              disabled={loading || !userId || !routeId}
              onClick={() => void handleStart()}
              className="h-11 w-full rounded-full border border-line bg-paper text-sm font-medium text-ink transition hover:border-sage disabled:opacity-60"
            >
              {t(language, "tripStart")}
            </button>
          </>
        ) : isCompleted ? (
          <p className="rounded-xl bg-sage-deep/10 px-4 py-3 text-center text-sm font-medium text-sage-deep">
            {t(language, "tripDone")}
          </p>
        ) : (
          <button
            type="button"
            disabled={loading || !currentPoiId || currentPoiChecked}
            onClick={() => void handleSimulateArrive()}
            className="h-11 w-full rounded-full bg-sage-deep text-sm font-medium text-paper hover:bg-moss disabled:opacity-60"
          >
            {loading
              ? t(language, "tripBusy")
              : currentPoiChecked
                ? t(language, "tripStopDone")
                : !currentPoiId
                  ? t(language, "tripPickStop")
                  : !currentPoiBelongsToTrip
                    ? t(language, "tripSimulateArrive")
                    : t(language, "tripSimulateArrive")}
          </button>
        )}

        {isCurrentRoute && trip ? (
          <Link
            to={postcardHref}
            className={[
              "flex h-11 w-full items-center justify-center rounded-full border text-sm font-medium transition",
              currentPoiChecked
                ? "border-sage-deep bg-sage-deep/10 text-sage-deep hover:bg-sage-deep hover:text-paper"
                : "border-line bg-paper text-ink hover:border-sage",
            ].join(" ")}
          >
            {currentPoiChecked
              ? t(language, "postcardMakeThis")
              : t(language, "postcardOpenGallery")}
          </Link>
        ) : null}
      </div>
    </section>
  );
}
