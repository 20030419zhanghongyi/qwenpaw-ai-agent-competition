import type { Postcard } from "@/types/postcards";
import { postcardImageSrc } from "@/api/postcards";
import { t } from "@/i18n";
import type { LanguageCode } from "@/types";
import { photoStyleLabelKey } from "@/components/postcard/photoStyles";
import { localizedPoiName } from "@/lib/poiLocalization";

export function PostcardCard({
  postcard,
  language,
  onOpen,
  compact,
}: {
  postcard: Postcard;
  language: LanguageCode;
  onOpen?: () => void;
  compact?: boolean;
}) {
  const src = postcardImageSrc(postcard.image_url);
  const poiName = localizedPoiName(postcard, language);
  const metaBits = [
    postcard.task_label,
    postcard.timestamp_label,
    postcard.geo_label,
  ].filter(Boolean);

  return (
    <article
      className={[
        "overflow-hidden rounded-2xl border border-line bg-card shadow-[var(--shadow-soft)]",
        onOpen ? "transition hover:border-sage" : "",
      ].join(" ")}
    >
      <button
        type="button"
        disabled={!onOpen}
        onClick={onOpen}
        className="block w-full text-left disabled:cursor-default"
      >
        <div
          className={[
            "bg-paper-warm",
            compact ? "aspect-[3/2]" : "aspect-[3/2] sm:aspect-[1.5/1]",
          ].join(" ")}
        >
          <img
            src={src}
            alt={poiName}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        </div>
        <div className="px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-display text-lg text-ink">{poiName}</p>
            {postcard.ai_generated ? (
              <span className="rounded-full bg-sage-deep/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-sage-deep">
                {t(language, "postcardAiBadge")}
              </span>
            ) : null}
            {postcard.photo_scrubbed ? (
              <span className="rounded-full bg-paper-warm px-2 py-0.5 text-[10px] text-ink-soft">
                {t(language, "postcardScrubbed")}
              </span>
            ) : postcard.scene_source === "ai" || postcard.scene_source === "library" ? (
              <span className="rounded-full bg-sage-deep/10 px-2 py-0.5 text-[10px] font-semibold text-sage-deep">
                {t(language, "postcardAiSceneBadge")}
              </span>
            ) : postcard.has_user_photo === false ? (
              <span className="rounded-full bg-paper-warm px-2 py-0.5 text-[10px] text-ink-soft">
                {t(language, "postcardNoPhotoBadge")}
              </span>
            ) : null}
            {postcard.scene_source === "ai_edit" ? (
              <span className="rounded-full bg-sage-deep/10 px-2 py-0.5 text-[10px] font-semibold text-sage-deep">
                {t(language, "postcardAiStyleBadge")} ·{" "}
                {t(language, photoStyleLabelKey(postcard.photo_style))}
              </span>
            ) : postcard.scene_source === "ai" || postcard.scene_source === "library" ? (
              <span className="rounded-full bg-sage-deep/10 px-2 py-0.5 text-[10px] font-semibold text-sage-deep">
                {t(language, "postcardAiSceneBadge")}
              </span>
            ) : !postcard.photo_scrubbed && postcard.has_user_photo === false ? (
              <span className="rounded-full bg-paper-warm px-2 py-0.5 text-[10px] text-ink-soft">
                {t(language, "postcardNoPhotoBadge")}
              </span>
            ) : null}
          </div>
          {metaBits.length > 0 ? (
            <p className="mt-1 text-[11px] leading-relaxed text-ink-soft">
              {metaBits.join(" · ")}
            </p>
          ) : null}
          <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-ink-soft">
            {postcard.caption}
          </p>
        </div>
      </button>
    </article>
  );
}
