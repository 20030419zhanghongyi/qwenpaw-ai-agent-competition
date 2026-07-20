import { useEffect } from "react";
import { useTrip } from "@/state/TripContext";

export interface TripControlsProps {
  userId: string;
  routeId: string;
  currentPoiId?: string;
}

export function TripControls({
  userId,
  routeId,
  currentPoiId,
}: TripControlsProps) {
  const {
    trip,
    progress,
    loading,
    error,
    startTrip,
    loadCurrentTrip,
    checkIn,
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
    Boolean(currentPoiId) && Boolean(trip?.checked_in_poi_ids.includes(currentPoiId ?? ""));
  const currentPoiBelongsToTrip =
    Boolean(currentPoiId) && Boolean(trip?.stop_poi_ids.includes(currentPoiId ?? ""));

  const handleStart = async () => {
    try {
      await startTrip(userId, routeId);
    } catch {
      // The context exposes the backend error for display.
    }
  };

  const handleCheckIn = async () => {
    if (!currentPoiId) return;
    try {
      await checkIn(currentPoiId);
    } catch {
      // The context exposes the backend error for display.
    }
  };

  return (
    <section className="rounded-2xl border border-line bg-card p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-sage-deep">
            行程进度
          </p>
          {isCurrentRoute && progress ? (
            <p className="mt-1 text-sm text-ink">
              已完成 {progress.completed_stops}/{progress.total_stops} 站
            </p>
          ) : (
            <p className="mt-1 text-sm text-ink-soft">尚未开始当前路线</p>
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

      {error ? (
        <p role="alert" className="mt-3 text-sm text-clay">
          {error}
        </p>
      ) : null}

      <div className="mt-4">
        {!isCurrentRoute ? (
          <>
            {trip?.status === "active" ? (
              <p className="mb-3 text-xs text-ink-soft">
                你有另一条进行中的路线；开始当前路线会创建新的行程。
              </p>
            ) : null}
            <button
              type="button"
              disabled={loading || !userId || !routeId}
              onClick={() => void handleStart()}
              className="h-11 w-full rounded-full bg-sage-deep text-sm font-medium text-paper hover:bg-moss disabled:opacity-60"
            >
              {loading ? "处理中…" : "开始行程"}
            </button>
          </>
        ) : isCompleted ? (
          <p className="rounded-xl bg-sage-deep/10 px-4 py-3 text-center text-sm font-medium text-sage-deep">
            行程完成
          </p>
        ) : (
          <button
            type="button"
            disabled={
              loading ||
              !currentPoiId ||
              currentPoiChecked ||
              !currentPoiBelongsToTrip
            }
            onClick={() => void handleCheckIn()}
            className="h-11 w-full rounded-full bg-sage-deep text-sm font-medium text-paper hover:bg-moss disabled:opacity-60"
          >
            {loading
              ? "处理中…"
              : currentPoiChecked
                ? "本站已完成"
                : !currentPoiId
                  ? "请选择当前站点"
                  : !currentPoiBelongsToTrip
                    ? "该站点不在行程中"
                    : "完成本站"}
          </button>
        )}
      </div>
    </section>
  );
}
