import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { checkInTrip, TripApiError } from "@/api/trips";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { PostcardCreateForm } from "@/components/postcard/PostcardCreateForm";
import { t } from "@/i18n";
import { resolveTripUserId } from "@/lib/guestUser";
import { useAuth } from "@/state/AuthContext";
import { useTrip } from "@/state/TripContext";
import { useWalk } from "@/state/WalkContext";

export function PostcardCreatePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { language, session } = useWalk();
  const { userId: authUserId } = useAuth();
  const { trip, loadTrip, simulateArrive, loading: tripLoading } = useTrip();
  const [arriveBusy, setArriveBusy] = useState(false);
  const [arriveError, setArriveError] = useState<string | null>(null);

  const tripId = searchParams.get("trip") || trip?.trip_id || "";
  const routeId = trip?.route_id || session?.match.route.id || "";
  const walkStopIds = useMemo(() => {
    const nodes = [...(session?.match.route.nodes ?? [])].sort(
      (a, b) => a.order - b.order,
    );
    return nodes.map((node) => node.poi_id).filter(Boolean);
  }, [session?.match.route.nodes]);
  const lastChecked =
    trip && trip.checked_in_poi_ids.length > 0
      ? trip.checked_in_poi_ids[trip.checked_in_poi_ids.length - 1]
      : "";
  const poiId = searchParams.get("poi") || lastChecked;

  useEffect(() => {
    if (!tripId || trip?.trip_id === tripId) return;
    void loadTrip(tripId).catch(() => {
      // Create form still works; check-in hint may be incomplete.
    });
  }, [loadTrip, trip?.trip_id, tripId]);

  const poiName = useMemo(() => {
    if (!poiId) return undefined;
    return session?.poisById[poiId]?.poi_name;
  }, [poiId, session]);

  const checkedIn = Boolean(trip && poiId && trip.checked_in_poi_ids.includes(poiId));

  const handleSimulateArrive = async () => {
    if (!poiId) return;
    setArriveError(null);
    setArriveBusy(true);
    try {
      const uid = resolveTripUserId(authUserId);
      if (routeId) {
        // Rebuild trip from current walk nodes when the stored trip is stale
        // after route adjust / named POI insert.
        await simulateArrive(uid, routeId, poiId, walkStopIds);
        return;
      }
      if (tripId) {
        await checkInTrip(tripId, { poi_id: poiId });
        await loadTrip(tripId);
        return;
      }
      setArriveError(t(language, "postcardMissingContext"));
    } catch (err) {
      const message =
        err instanceof TripApiError || err instanceof Error ? err.message : "";
      setArriveError(
        message === "TRIP_BACKEND_STALE"
          ? t(language, "tripBackendStale")
          : message === "TRIP_POI_MISMATCH" || /not part of trip/i.test(message)
            ? t(language, "tripPoiMismatch")
            : message || t(language, "tripSimulateArriveError"),
      );
    } finally {
      setArriveBusy(false);
    }
  };

  if (!tripId || !poiId) {
    return (
      <main className="mx-auto max-w-lg flex-1 px-5 py-10">
        <p className="font-display text-2xl text-ink">{t(language, "postcardMissingContext")}</p>
        <p className="mt-2 text-sm text-ink-soft">{t(language, "postcardMissingContextLead")}</p>
        <Link
          to="/walk"
          className="mt-6 inline-flex h-11 items-center rounded-full bg-sage-deep px-6 text-sm font-medium text-paper hover:bg-moss"
        >
          {t(language, "postcardGoWalk")}
        </Link>
      </main>
    );
  }

  const busy = arriveBusy || tripLoading;

  return (
    <main className="relative flex-1 bg-paper pb-24">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-48 bg-[radial-gradient(ellipse_at_top,_oklch(0.62_0.038_145_/_0.1),_transparent_70%)]"
      />
      <div className="relative mx-auto max-w-lg px-5 pt-8">
        <Link
          to={`/postcards?trip=${encodeURIComponent(tripId)}`}
          className="mb-6 inline-block text-sm text-ink-soft transition hover:text-ink"
        >
          {t(language, "postcardBackToGallery")}
        </Link>

        <AzulejoBand className="mb-8" />

        {!checkedIn ? (
          <div className="mb-6 space-y-3 rounded-2xl border border-line bg-card px-4 py-4 shadow-[var(--shadow-soft)]">
            <p className="text-sm text-ink-soft">{t(language, "postcardNeedCheckin")}</p>
            <p className="text-[11px] leading-relaxed text-ink-soft">
              {t(language, "tripDemoHint")}
            </p>
            {arriveError ? (
              <p role="alert" className="text-sm text-clay">
                {arriveError}
              </p>
            ) : null}
            <button
              type="button"
              disabled={busy}
              onClick={() => void handleSimulateArrive()}
              className="h-11 w-full rounded-full bg-sage-deep text-sm font-medium text-paper hover:bg-moss disabled:opacity-60"
            >
              {busy ? t(language, "tripBusy") : t(language, "tripSimulateArrive")}
            </button>
          </div>
        ) : null}

        {checkedIn ? (
          <PostcardCreateForm
            tripId={tripId}
            poiId={poiId}
            poiName={poiName}
            language={language}
            replace={searchParams.get("replace") === "1"}
            onCreated={(postcard) => {
              navigate(
                `/postcards/${encodeURIComponent(postcard.postcard_id)}?trip=${encodeURIComponent(postcard.trip_id)}`,
                { replace: true, state: { postcard } },
              );
            }}
            onSkip={() => navigate(`/postcards?trip=${encodeURIComponent(tripId)}`)}
          />
        ) : null}
      </div>
    </main>
  );
}
