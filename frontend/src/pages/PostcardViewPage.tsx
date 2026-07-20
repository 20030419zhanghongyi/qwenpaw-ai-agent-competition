import { useEffect, useState } from "react";
import { Link, useLocation, useParams, useSearchParams } from "react-router-dom";
import { listTripPostcards, postcardImageSrc, PostcardApiError } from "@/api/postcards";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { ErrorState, LoadingState } from "@/components/common/States";
import { PostcardActions } from "@/components/postcard/PostcardActions";
import { t } from "@/i18n";
import { useWalk } from "@/state/WalkContext";
import type { Postcard } from "@/types/postcards";

export function PostcardViewPage() {
  const { postcardId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const { language } = useWalk();
  const tripId = searchParams.get("trip");
  const fromState = (location.state as { postcard?: Postcard } | null)?.postcard;

  const [postcard, setPostcard] = useState<Postcard | null>(
    fromState?.postcard_id === postcardId ? fromState : null,
  );
  const [loading, setLoading] = useState(!postcard);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (postcard || !postcardId) return;
    if (!tripId) {
      setLoading(false);
      setError(t(language, "postcardMissingContext"));
      return;
    }
    let cancelled = false;
    setLoading(true);
    void listTripPostcards(tripId)
      .then((cards) => {
        if (cancelled) return;
        const found = cards.find((card) => card.postcard_id === postcardId) ?? null;
        setPostcard(found);
        if (!found) setError(t(language, "postcardNotFound"));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message =
          err instanceof PostcardApiError || err instanceof Error ? err.message : "";
        setError(
          message.includes("Failed to fetch")
            ? t(language, "backendDown")
            : message || t(language, "postcardLoadError"),
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [language, postcard, postcardId, tripId]);

  const galleryHref = tripId
    ? `/postcards?trip=${encodeURIComponent(tripId)}`
    : "/postcards";

  return (
    <main className="relative flex-1 bg-paper pb-24">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-56 bg-[radial-gradient(ellipse_at_top,_oklch(0.62_0.038_145_/_0.12),_transparent_65%)]"
      />
      <div className="relative mx-auto max-w-2xl px-5 pt-8">
        <Link
          to={galleryHref}
          className="mb-6 inline-block text-sm text-ink-soft transition hover:text-ink"
        >
          {t(language, "postcardBackToGallery")}
        </Link>

        <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
          {t(language, "postcardEyebrow")}
        </p>
        <h1 className="mb-6 font-display text-3xl text-ink">
          {postcard?.poi_name ?? t(language, "postcardViewTitle")}
        </h1>

        <AzulejoBand className="mb-8" />

        {loading ? <LoadingState label={t(language, "postcardLoading")} /> : null}

        {!loading && error ? (
          <ErrorState title={t(language, "errorTitle")} message={error} />
        ) : null}

        {!loading && postcard ? (
          <div className="space-y-6">
            <div className="overflow-hidden rounded-[1.75rem] border border-line bg-card shadow-[var(--shadow-lift)]">
              <img
                src={postcardImageSrc(postcard.image_url)}
                alt={postcard.poi_name}
                className="w-full bg-paper-warm"
              />
            </div>

            <div className="rounded-2xl border border-line bg-card px-5 py-5 shadow-[var(--shadow-soft)]">
              <div className="flex flex-wrap items-center gap-2">
                {postcard.ai_generated ? (
                  <span className="rounded-full bg-sage-deep/10 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-sage-deep">
                    {t(language, "postcardAiBadge")}
                  </span>
                ) : null}
                {postcard.photo_scrubbed ? (
                  <span className="rounded-full bg-paper-warm px-2.5 py-0.5 text-[10px] text-ink-soft">
                    {t(language, "postcardScrubbed")}
                  </span>
                ) : null}
              </div>
              <p className="mt-3 font-display text-xl leading-snug text-ink">
                {postcard.caption}
              </p>
              <p className="mt-3 text-xs text-ink-soft">
                {new Date(postcard.created_at).toLocaleDateString(language)} · Macau
              </p>
            </div>

            <PostcardActions postcard={postcard} language={language} />
          </div>
        ) : null}
      </div>
    </main>
  );
}
