import { useState } from "react";
import type { GuideNarrationSection } from "@/api/client";
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

export function GuideNarrationSections({
  language,
  sections,
  imageUrl,
  imageAlt,
  showImage,
}: {
  language: LanguageCode;
  sections: GuideNarrationSection[];
  imageUrl?: string | null;
  imageAlt?: string;
  showImage?: boolean;
}) {
  const [imageBroken, setImageBroken] = useState(false);

  if (!sections.length) return null;

  const historyIdx = sections.findIndex((s) => s.id === "history");
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

      <ol className="divide-y divide-line/50">
        {sections.map((section, index) => {
          const isHistory = section.id === "history";
          const isFirstHistory = isHistory && historyIdx === index;
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
              <p
                className={[
                  "whitespace-pre-wrap leading-relaxed text-ink",
                  isFirstHistory ? "text-[15px] sm:text-base" : "text-sm",
                ].join(" ")}
              >
                {section.body}
              </p>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
