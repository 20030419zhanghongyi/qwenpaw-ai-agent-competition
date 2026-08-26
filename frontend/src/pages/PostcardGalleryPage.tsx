import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { listTripPostcards, PostcardApiError } from "@/api/postcards";
import { listTripHistory } from "@/api/profile";
import { getCurrentTrip, TripApiError } from "@/api/trips";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { ErrorState, LoadingState } from "@/components/common/States";
import { PostcardCard } from "@/components/postcard/PostcardCard";
import { TravelMemory } from "@/components/postcard/TravelMemory";
import { ProfileSidebar } from "@/components/profile/ProfileSidebar";
import { t } from "@/i18n";
import { resolveTripUserId } from "@/lib/guestUser";
import { getLastTripId, rememberLastTripId } from "@/lib/lastTrip";
import { localizedPoiName } from "@/lib/poiLocalization";
import { useAuth } from "@/state/AuthContext";
import { useTrip } from "@/state/TripContext";
import { useWalk } from "@/state/WalkContext";
import type { Postcard } from "@/types/postcards";

export function PostcardGalleryPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { language, session } = useWalk();
  const { userId: authUserId } = useAuth();
  const { trip, loadTrip } = useTrip();
  const [postcards, setPostcards] = useState<Postcard[]>([]);
  const [resolvedTripId, setResolvedTripId] = useState<string | null>(
    searchParams.get("trip") || getLastTripId(),
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const tripIdFromQuery = searchParams.get("trip");

  const checkedInStops = useMemo(() => {
    if (!trip || !session) return [];
    return trip.stop_poi_ids
      .filter((poiId) => trip.checked_in_poi_ids.includes(poiId))
      .map((poiId) => ({
        poiId,
        name: session.poisById[poiId]
          ? localizedPoiName(session.poisById[poiId], language)
          : poiId,
        hasPostcard: postcards.some((card) => card.poi_id === poiId),
      }));
  }, [trip, session, postcards, language]);

  const refresh = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      if (!tripIdFromQuery && authUserId) {
        const history = await listTripHistory(authUserId);
        if (history.length === 0) {
          setResolvedTripId(null);
          setPostcards([]);
          return;
        }

        const allPostcards = (
          await Promise.all(history.map(({ trip_id }) => listTripPostcards(trip_id)))
        )
          .flat()
          .sort(
            (left, right) =>
              new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
          );
        const rememberedTripId = getLastTripId();
        const selectedTripId =
          history.find(({ trip_id }) => trip_id === rememberedTripId)?.trip_id ??
          history[0].trip_id;
        setResolvedTripId(selectedTripId);
        rememberLastTripId(selectedTripId);
        await loadTrip(selectedTripId);
        setPostcards(allPostcards);
        return;
      }

      let tripId = tripIdFromQuery || getLastTripId();
      if (!tripId) {
        try {
          const current = await getCurrentTrip(resolveTripUserId(authUserId));
          tripId = current.trip.trip_id;
        } catch (err) {
          if (err instanceof TripApiError && err.status === 404) {
            setResolvedTripId(null);
            setPostcards([]);
            return;
          }
          throw err;
        }
      }

      setResolvedTripId(tripId);
      rememberLastTripId(tripId);
      await loadTrip(tripId);
      setPostcards(await listTripPostcards(tripId));
    } catch (err) {
      const message =
        err instanceof PostcardApiError ||
        err instanceof TripApiError ||
        err instanceof Error
          ? err.message
          : "";
      setError(
        message.includes("Failed to fetch")
          ? t(language, "backendDown")
          : message || t(language, "postcardLoadError"),
      );
    } finally {
      setLoading(false);
    }
  }, [authUserId, language, loadTrip, tripIdFromQuery]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const createHref = (poiId: string) => {
    const id = resolvedTripId || trip?.trip_id;
    if (!id) return "/walk";
    return `/postcards/new?trip=${encodeURIComponent(id)}&poi=${encodeURIComponent(poiId)}`;
  };

  const hasTrip = Boolean(resolvedTripId || trip);

  return (
    <main className="relative flex-1 bg-paper pb-24">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-56 bg-[radial-gradient(ellipse_at_top,_oklch(0.62_0.038_145_/_0.12),_transparent_65%)]"
      />
      <div className="relative mx-auto max-w-6xl px-5 pt-8 lg:px-8">
        <Link
          to="/walk"
          className="mb-6 inline-block text-sm text-ink-soft transition hover:text-ink"
        >
          {t(language, "postcardBackToWalk")}
        </Link>

        <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
          {t(language, "postcardEyebrow")}
        </p>
        <h1 className="mb-2 font-display text-3xl leading-tight text-ink lg:text-4xl">
          {t(language, "postcardGalleryTitle")}
        </h1>
        <p className="mb-8 max-w-lg text-sm leading-relaxed text-ink-soft">
          {t(language, "postcardGalleryLead")}
        </p>

        <div className="grid min-w-0 gap-8 lg:grid-cols-[13rem_minmax(0,1fr)]">
          <ProfileSidebar language={language} />
          <div className="min-w-0">
            <AzulejoBand className="mb-8" />

            {loading ? <LoadingState label={t(language, "postcardLoading")} /> : null}

            {!loading && error ? (
              <ErrorState
                title={t(language, "errorTitle")}
                message={error}
                onRetry={() => void refresh()}
                retryLabel={t(language, "retry")}
              />
            ) : null}

            {!loading && !error && !hasTrip ? (
              <div className="rounded-2xl border border-line bg-card px-5 py-8 text-center shadow-[var(--shadow-soft)]">
                <p className="font-display text-xl text-ink">
                  {t(language, "postcardNoTripTitle")}
                </p>
                <p className="mt-2 text-sm text-ink-soft">
                  {t(language, "postcardNoTripLead")}
                </p>
                <Link
                  to="/walk"
                  className="mt-6 inline-flex h-11 items-center rounded-full bg-sage-deep px-6 text-sm font-medium text-paper transition hover:bg-moss"
                >
                  {t(language, "postcardGoWalk")}
                </Link>
              </div>
            ) : null}

            {!loading && !error && hasTrip ? (
              <>
            <TravelMemory postcards={postcards} language={language} />
            {postcards.length === 0 ? (
              <div className="mb-8 rounded-2xl border border-line bg-card px-5 py-8 text-center shadow-[var(--shadow-soft)]">
                <p className="font-display text-xl text-ink">
                  {t(language, "postcardEmptyTitle")}
                </p>
                <p className="mt-2 text-sm text-ink-soft">{t(language, "postcardEmptyLead")}</p>
              </div>
            ) : (
              <div className="mb-10 grid gap-5 sm:grid-cols-2">
                {postcards.map((card) => (
                  <PostcardCard
                    key={card.postcard_id}
                    postcard={card}
                    language={language}
                    onOpen={() =>
                      navigate(
                        `/postcards/${encodeURIComponent(card.postcard_id)}?trip=${encodeURIComponent(card.trip_id)}`,
                      )
                    }
                  />
                ))}
              </div>
            )}

            {checkedInStops.length > 0 ? (
              <section className="rounded-[1.75rem] border border-sage-deep/20 bg-gradient-to-b from-card to-paper-warm px-5 py-6 shadow-[var(--shadow-soft)]">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
                  {t(language, "postcardMakeMore")}
                </p>
                <ul className="mt-4 space-y-3">
                  {checkedInStops.map((stop) => (
                    <li
                      key={stop.poiId}
                      className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3 last:border-0 last:pb-0"
                    >
                      <span className="text-sm text-ink">{stop.name}</span>
                      {stop.hasPostcard ? (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-ink-soft">
                            {t(language, "postcardAlreadyMade")}
                          </span>
                          <Link
                            to={`${createHref(stop.poiId)}&replace=1`}
                            className="rounded-full border border-sage-deep px-4 py-1.5 text-xs font-medium text-sage-deep transition hover:bg-sage-deep hover:text-paper"
                          >
                            {t(language, "postcardRemake")}
                          </Link>
                        </div>
                      ) : (
                        <Link
                          to={createHref(stop.poiId)}
                          className="rounded-full border border-sage-deep px-4 py-1.5 text-xs font-medium text-sage-deep transition hover:bg-sage-deep hover:text-paper"
                        >
                          {t(language, "postcardMakeThis")}
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            ) : postcards.length === 0 ? (
              <p className="text-center text-sm text-ink-soft">
                {t(language, "postcardNeedCheckinHint")}
              </p>
            ) : null}
              </>
            ) : null}
          </div>
        </div>
      </div>
    </main>
  );
}
