import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { listTripPostcards, postcardImageSrc, PostcardApiError } from "@/api/postcards";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { ErrorState, LoadingState } from "@/components/common/States";
import { PostcardActions } from "@/components/postcard/PostcardActions";
import { photoStyleLabelKey } from "@/components/postcard/photoStyles";
import { t } from "@/i18n";
import { useWalk } from "@/state/WalkContext";
import type { Postcard } from "@/types/postcards";

export function PostcardViewPage() {
  const { postcardId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
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

  function goCreateForPoi(poiId: string) {
    if (!tripId) {
      navigate(galleryHref, { replace: true });
      return;
    }
    navigate(
      `/postcards/new?trip=${encodeURIComponent(tripId)}&poi=${encodeURIComponent(poiId)}&replace=1`,
      { replace: true },
    );
  }

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
                ) : postcard.scene_source === "ai" || postcard.scene_source === "library" ? (
                  <span className="rounded-full bg-sage-deep/10 px-2.5 py-0.5 text-[10px] font-semibold text-sage-deep">
                    {t(language, "postcardAiSceneBadge")}
                  </span>
                ) : postcard.has_user_photo === false ? (
                  <span className="rounded-full bg-paper-warm px-2.5 py-0.5 text-[10px] text-ink-soft">
                    {t(language, "postcardNoPhotoBadge")}
                  </span>
                ) : null}
                {postcard.scene_source === "ai_edit" ? (
                  <span className="rounded-full bg-sage-deep/10 px-2.5 py-0.5 text-[10px] font-semibold text-sage-deep">
                    {t(language, "postcardAiStyleBadge")} ·{" "}
                    {t(language, photoStyleLabelKey(postcard.photo_style))}
                  </span>
                ) : postcard.scene_source === "ai" || postcard.scene_source === "library" ? (
                  <span className="rounded-full bg-sage-deep/10 px-2.5 py-0.5 text-[10px] font-semibold text-sage-deep">
                    {t(language, "postcardAiSceneBadge")}
                  </span>
                ) : !postcard.photo_scrubbed && postcard.has_user_photo === false ? (
                  <span className="rounded-full bg-paper-warm px-2.5 py-0.5 text-[10px] text-ink-soft">
                    {t(language, "postcardNoPhotoBadge")}
                  </span>
                ) : null}
              </div>
              {postcard.task_label ? (
                <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-sage-deep">
                  {postcard.task_label}
                </p>
              ) : null}
              <p className="mt-3 font-display text-xl leading-snug text-ink">
                {postcard.caption}
              </p>
              <dl className="mt-4 space-y-2 text-xs text-ink-soft">
                <div className="flex gap-2">
                  <dt className="shrink-0 font-medium text-ink/70">
                    {t(language, "postcardStampTime")}
                  </dt>
                  <dd>
                    {postcard.timestamp_label ||
                      `${new Date(postcard.created_at).toLocaleString(language)} · Macau`}
                  </dd>
                </div>
                {postcard.geo_label ? (
                  <div className="flex gap-2">
                    <dt className="shrink-0 font-medium text-ink/70">
                      {t(language, "postcardStampGeo")}
                    </dt>
                    <dd>{postcard.geo_label}</dd>
                  </div>
                ) : null}
                {postcard.route_name ? (
                  <div className="flex gap-2">
                    <dt className="shrink-0 font-medium text-ink/70">
                      {t(language, "postcardStampRoute")}
                    </dt>
                    <dd>{postcard.route_name}</dd>
                  </div>
                ) : null}
              </dl>
            </div>

            <PostcardActions
              postcard={postcard}
              language={language}
              onDeleted={() => navigate(galleryHref, { replace: true })}
              onRegenerate={() => goCreateForPoi(postcard.poi_id)}
            />
          </div>
        ) : null}
      </div>
    </main>
  );
}
