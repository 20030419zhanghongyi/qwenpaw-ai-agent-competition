import { useState, type ReactNode } from "react";
import type {
  GuideNarrationSection,
  ImmersiveGuide,
} from "@/api/client";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { t } from "@/i18n";
import type { LanguageCode } from "@/types";

const SECTION_I18N: Record<
  string,
  | "guideSectionOverview"
  | "guideSectionHistory"
  | "guideSectionArchitecture"
  | "guideSectionStory"
> = {
  overview: "guideSectionOverview",
  history: "guideSectionHistory",
  architecture: "guideSectionArchitecture",
  story: "guideSectionStory",
};

/** Split a flat script into display sections when API has no ``sections``. */
export function sectionsFromText(text: string): GuideNarrationSection[] {
  const raw = (text || "").trim();
  if (!raw) return [];
  const parts = raw
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);
  if (parts.length >= 2) {
    const ids = ["overview", "history", "architecture", "story"] as const;
    return parts.slice(0, 4).map((body, i) => ({
      id: ids[Math.min(i, ids.length - 1)],
      body,
    }));
  }
  // Single blob: soft-split on sentence boundaries into ~2–3 blocks
  const sentences = raw
    .replace(/([。！？!?])\s*/g, "$1\n")
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
  if (sentences.length <= 2) {
    return [{ id: "overview", body: raw }];
  }
  const chunk = Math.max(1, Math.ceil(sentences.length / 3));
  const blocks: GuideNarrationSection[] = [];
  const ids = ["overview", "history", "architecture"] as const;
  for (let i = 0; i < sentences.length && blocks.length < 3; i += chunk) {
    blocks.push({
      id: ids[blocks.length] ?? "overview",
      body: sentences.slice(i, i + chunk).join(""),
    });
  }
  return blocks;
}

function sectionTitle(language: LanguageCode, id: string): string {
  const key = SECTION_I18N[id];
  if (key) return t(language, key);
  return id;
}

function hasImmersiveContent(immersive?: ImmersiveGuide | null): boolean {
  if (!immersive) return false;
  return Boolean(
    immersive.hook ||
      immersive.why_it_matters ||
      immersive.historical_story ||
      (immersive.things_to_observe && immersive.things_to_observe.length > 0) ||
      immersive.local_story ||
      immersive.interactive_suggestion,
  );
}

function ImmersiveNarration({
  language,
  immersive,
}: {
  language: LanguageCode;
  immersive: ImmersiveGuide;
}) {
  const observations = (immersive.things_to_observe || []).filter((o) =>
    (o.observation || "").trim(),
  );
  const next = immersive.next_exploration;
  const nextBits = [
    next?.distance,
    next?.walk_time,
  ].filter((x) => (x || "").trim());

  const blocks: Array<{
    key: string;
    label: string;
    body: ReactNode;
    emphasize?: boolean;
  }> = [];

  if (immersive.hook?.trim()) {
    blocks.push({
      key: "hook",
      label: t(language, "guideImmersiveHook"),
      body: immersive.hook,
      emphasize: true,
    });
  }
  if (immersive.why_it_matters?.trim()) {
    blocks.push({
      key: "why",
      label: t(language, "guideImmersiveWhy"),
      body: immersive.why_it_matters,
    });
  }
  if (immersive.historical_story?.trim()) {
    blocks.push({
      key: "history",
      label: t(language, "guideImmersiveHistory"),
      body: immersive.historical_story,
      emphasize: true,
    });
  }
  if (observations.length) {
    blocks.push({
      key: "observe",
      label: t(language, "guideImmersiveObserve"),
      body: (
        <ul className="space-y-3">
          {observations.map((item, i) => (
            <li key={`obs-${i}`} className="text-sm leading-relaxed text-ink">
              <p className="font-medium text-ink">{item.observation}</p>
              {item.explanation?.trim() ? (
                <p className="mt-1 text-ink-soft">{item.explanation}</p>
              ) : null}
            </li>
          ))}
        </ul>
      ),
    });
  }
  if (immersive.local_story?.trim()) {
    blocks.push({
      key: "local",
      label: t(language, "guideImmersiveLocal"),
      body: immersive.local_story,
    });
  }
  if (immersive.interactive_suggestion?.trim()) {
    blocks.push({
      key: "interactive",
      label: t(language, "guideImmersiveInteractive"),
      body: immersive.interactive_suggestion,
    });
  }
  if (next?.location?.trim() || next?.reason?.trim()) {
    blocks.push({
      key: "next",
      label: t(language, "guideImmersiveNext"),
      body: (
        <div className="space-y-1 text-sm leading-relaxed text-ink">
          {next?.location?.trim() ? (
            <p className="font-medium">{next.location}</p>
          ) : null}
          {nextBits.length ? (
            <p className="text-xs text-ink-soft">{nextBits.join(" · ")}</p>
          ) : null}
          {next?.reason?.trim() ? (
            <p className="text-ink-soft">{next.reason}</p>
          ) : null}
        </div>
      ),
    });
  }

  return (
    <div className="space-y-1">
      {(immersive.title || immersive.subtitle) && (
        <header className="mb-4">
          {immersive.title ? (
            <h3 className="font-display text-xl text-ink sm:text-2xl">
              {immersive.title}
            </h3>
          ) : null}
          {immersive.subtitle ? (
            <p className="mt-1 text-xs uppercase tracking-[0.16em] text-sage-deep">
              {immersive.subtitle}
            </p>
          ) : null}
        </header>
      )}
      <ol className="divide-y divide-line/50">
        {blocks.map((block, index) => (
          <li key={block.key} className="py-5 first:pt-0 last:pb-0">
            <div className="mb-2 flex items-baseline gap-2">
              <span
                className={[
                  "font-display text-[11px] tabular-nums tracking-[0.14em]",
                  block.emphasize ? "text-sage-deep" : "text-ink-soft",
                ].join(" ")}
                aria-hidden
              >
                {String(index + 1).padStart(2, "0")}
              </span>
              <h4
                className={[
                  "text-[11px] uppercase tracking-[0.18em]",
                  block.emphasize
                    ? "font-bold text-sage-deep"
                    : "font-semibold text-ink-soft",
                ].join(" ")}
              >
                {block.label}
              </h4>
            </div>
            {typeof block.body === "string" ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
                {block.body}
              </p>
            ) : (
              block.body
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

export function GuideNarrationSections({
  language,
  sections,
  immersive,
  imageUrl,
  imageAlt,
  showImage,
}: {
  language: LanguageCode;
  sections: GuideNarrationSection[];
  immersive?: ImmersiveGuide | null;
  imageUrl?: string | null;
  imageAlt?: string;
  showImage?: boolean;
}) {
  const [imageBroken, setImageBroken] = useState(false);
  const useImmersive = hasImmersiveContent(immersive);

  if (!useImmersive && !sections.length) return null;

  const pictorial = Boolean(showImage && imageUrl && !imageBroken);

  return (
    <div className="mt-4 space-y-4">
      {pictorial ? (
        <figure className="overflow-hidden rounded-2xl border border-sage-deep/15 bg-moss/5">
          <div className="relative aspect-[16/9] overflow-hidden sm:aspect-[2/1]">
            <img
              src={imageUrl!}
              alt={imageAlt || ""}
              className="h-full w-full object-cover"
              loading="lazy"
              onError={() => setImageBroken(true)}
            />
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-moss/35 via-transparent to-transparent" />
          </div>
          <AzulejoBand className="h-1.5" />
        </figure>
      ) : (
        <AzulejoBand className="h-1.5 rounded-full opacity-80" />
      )}

      {useImmersive && immersive ? (
        <ImmersiveNarration language={language} immersive={immersive} />
      ) : (
        <ol className="divide-y divide-line/50">
          {sections.map((section, index) => {
            const isHistory = section.id === "history";
            return (
              <li
                key={`${section.id}-${index}`}
                className="py-5 first:pt-0 last:pb-0"
              >
                <div className="mb-2 flex items-baseline gap-2">
                  <span
                    className={[
                      "font-display text-[11px] tabular-nums tracking-[0.14em]",
                      isHistory ? "text-sage-deep" : "text-ink-soft",
                    ].join(" ")}
                    aria-hidden
                  >
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <h3
                    className={[
                      "text-[11px] uppercase tracking-[0.18em]",
                      isHistory
                        ? "font-bold text-sage-deep"
                        : "font-semibold text-ink-soft",
                    ].join(" ")}
                  >
                    {sectionTitle(language, section.id)}
                  </h3>
                </div>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
                  {section.body}
                </p>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
