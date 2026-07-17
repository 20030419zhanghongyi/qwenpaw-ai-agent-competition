import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listPois, matchRoutes } from "@/api/client";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { ErrorState, LoadingState } from "@/components/common/States";
import { t } from "@/i18n";
import {
  applyPreferenceToForm,
  toPreference,
  type PreferenceFormState,
  type ThemeTag,
  type WalkTag,
} from "@/lib/preference";
import { useWalk } from "@/state/WalkContext";
import type { LanguageCode } from "@/types";

const LANGS: Array<{ code: LanguageCode; label: string }> = [
  { code: "zh-CN", label: "简体中文" },
  { code: "zh-TW", label: "繁體中文" },
  { code: "en", label: "English" },
  { code: "pt", label: "Português" },
];

const THEME_OPTIONS: Array<{
  id: ThemeTag;
  labelKey:
    | "themeHeritage"
    | "themeArchitecture"
    | "themePhoto"
    | "themeFood"
    | "themeFamily"
    | "themeLeisure"
    | "themeCotai";
}> = [
  { id: "heritage", labelKey: "themeHeritage" },
  { id: "architecture", labelKey: "themeArchitecture" },
  { id: "photo", labelKey: "themePhoto" },
  { id: "food", labelKey: "themeFood" },
  { id: "family", labelKey: "themeFamily" },
  { id: "leisure", labelKey: "themeLeisure" },
  { id: "cotai", labelKey: "themeCotai" },
];

const WALK_OPTIONS: Array<{
  id: WalkTag;
  labelKey:
    | "walkLess"
    | "walkNoBacktrack"
    | "walkShade"
    | "walkFlat"
    | "walkIndoor"
    | "walkAccessible";
}> = [
  { id: "less-walk", labelKey: "walkLess" },
  { id: "no-backtrack", labelKey: "walkNoBacktrack" },
  { id: "shade", labelKey: "walkShade" },
  { id: "flat", labelKey: "walkFlat" },
  { id: "indoor", labelKey: "walkIndoor" },
  { id: "accessible", labelKey: "walkAccessible" },
];

const emptyForm = (language: LanguageCode): PreferenceFormState => ({
  duration: "half",
  interests: [],
  themes: [],
  companion: "solo",
  walkTags: [],
  customNote: "",
  language,
});

export function ProfilePage() {
  const navigate = useNavigate();
  const { language, setLanguage, preference, session, updatePreference, saveMatch } =
    useWalk();
  const [duration, setDuration] = useState<PreferenceFormState["duration"]>("half");
  const [interests, setInterests] = useState<string[]>([]);
  const [themes, setThemes] = useState<ThemeTag[]>([]);
  const [companion, setCompanion] = useState<PreferenceFormState["companion"]>("solo");
  const [walkTags, setWalkTags] = useState<WalkTag[]>([]);
  const [savedFlash, setSavedFlash] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!preference) {
      setDuration("half");
      setInterests([]);
      setThemes([]);
      setCompanion("solo");
      setWalkTags([]);
      return;
    }
    const form = applyPreferenceToForm(preference, emptyForm(language));
    setDuration(form.duration);
    setInterests(form.interests);
    setThemes(form.themes);
    setCompanion(form.companion);
    setWalkTags(form.walkTags);
  }, [preference, language]);

  const snapshot = (): PreferenceFormState => ({
    duration,
    interests,
    themes,
    companion,
    walkTags,
    customNote: "",
    language,
  });

  const savePrefs = () => {
    const preference = toPreference(snapshot());
    updatePreference(preference);
    setSavedFlash(true);
    window.setTimeout(() => setSavedFlash(false), 1600);
  };

  const regenerate = async () => {
    setError(null);
    setLoading(true);
    try {
      const preference = toPreference(snapshot());
      updatePreference(preference);
      const [matchRes, pois] = await Promise.all([
        matchRoutes(preference),
        listPois({ limit: 500 }),
      ]);
      const top = matchRes.matches[0];
      if (!top) throw new Error(t(language, "noMatch"));
      const isMulti = preference.duration === "multi-day";
      saveMatch({
        preference: matchRes.preference,
        match: top,
        matches: isMulti ? matchRes.matches : [top],
        pois,
      });
      navigate("/walk");
    } catch (err) {
      const message = err instanceof Error ? err.message : "request failed";
      setError(
        message.includes("Failed to fetch") ? t(language, "backendDown") : message,
      );
    } finally {
      setLoading(false);
    }
  };

  const chip = (active: boolean) =>
    active
      ? "border-sage-deep bg-sage-deep text-paper"
      : "border-line bg-card text-ink hover:border-sage";

  return (
    <main className="relative flex-1 bg-paper pb-24">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-[radial-gradient(ellipse_at_top,_oklch(0.62_0.038_145_/_0.12),_transparent_65%)]"
      />
      <div className="relative mx-auto max-w-3xl px-5 pt-8 lg:px-0">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
          {t(language, "profileEyebrow")}
        </p>
        <h1 className="mb-2 font-display text-3xl leading-tight text-ink lg:text-4xl">
          {t(language, "profileTitle")}
        </h1>
        <p className="mb-8 max-w-lg text-sm leading-relaxed text-ink-soft">
          {t(language, "profileLead")}
        </p>

        <AzulejoBand className="mb-8" />

        <div className="overflow-hidden rounded-[1.75rem] border border-sage-deep/25 bg-gradient-to-b from-card via-card to-paper-warm shadow-[var(--shadow-soft)]">
          <div className="border-b border-line/80 bg-sage-deep/[0.06] px-5 py-4 sm:px-7">
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
              {t(language, "profilePanelLabel")}
            </p>
            <p className="mt-1 text-sm text-ink-soft">{t(language, "profilePanelHint")}</p>
          </div>

          <div className="divide-y divide-line/70 px-5 sm:px-7">
            <section className="py-6">
              <h2 className="mb-3 font-display text-xl text-ink">
                {t(language, "profileLanguage")}
              </h2>
              <div className="flex flex-wrap gap-2">
                {LANGS.map((l) => (
                  <button
                    key={l.code}
                    type="button"
                    onClick={() => setLanguage(l.code)}
                    className={`rounded-full border px-4 py-2 text-sm transition ${chip(language === l.code)}`}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
            </section>

            <section className="py-6">
              <h2 className="mb-1 font-display text-xl text-ink">{t(language, "durationTitle")}</h2>
              <p className="mb-3 text-xs text-ink-soft">{t(language, "durationCaption")}</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {(
                  [
                    ["half", "durationHalf"],
                    ["full", "durationFull"],
                    ["night", "durationNight"],
                    ["multi", "durationMulti"],
                  ] as const
                ).map(([id, key]) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setDuration(id)}
                    className={`rounded-2xl border px-3 py-3 text-sm transition ${chip(duration === id)}`}
                  >
                    {t(language, key)}
                  </button>
                ))}
              </div>
            </section>

            <section className="py-6">
              <h2 className="mb-1 font-display text-xl text-ink">{t(language, "themesTitle")}</h2>
              <p className="mb-3 text-xs text-ink-soft">{t(language, "themesCaption")}</p>
              <div className="flex flex-wrap gap-2">
                {THEME_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() =>
                      setThemes((s) =>
                        s.includes(opt.id) ? s.filter((x) => x !== opt.id) : [...s, opt.id],
                      )
                    }
                    className={`rounded-full border px-4 py-2 text-sm transition ${chip(themes.includes(opt.id))}`}
                  >
                    {t(language, opt.labelKey)}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-[11px] leading-relaxed text-ink-soft">
                {t(language, "themeCotaiHint")}
              </p>
            </section>

            <section className="py-6">
              <h2 className="mb-1 font-display text-xl text-ink">{t(language, "interestsTitle")}</h2>
              <p className="mb-3 text-xs text-ink-soft">{t(language, "interestsCaption")}</p>
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    ["history", "interestHistory"],
                    ["arch", "interestArch"],
                    ["food", "interestFood"],
                    ["photo", "interestPhoto"],
                    ["culture", "interestCulture"],
                    ["relax", "interestRelax"],
                  ] as const
                ).map(([id, key]) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() =>
                      setInterests((s) =>
                        s.includes(id) ? s.filter((x) => x !== id) : [...s, id],
                      )
                    }
                    className={`rounded-full border px-4 py-2 text-sm transition ${chip(interests.includes(id))}`}
                  >
                    {t(language, key)}
                  </button>
                ))}
              </div>
            </section>

            <section className="py-6">
              <h2 className="mb-1 font-display text-xl text-ink">{t(language, "companionTitle")}</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {(
                  [
                    ["solo", "companionSolo"],
                    ["friends", "companionFriends"],
                    ["family", "companionFamily"],
                  ] as const
                ).map(([id, key]) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setCompanion(id)}
                    className={`rounded-full border px-4 py-2 text-sm transition ${chip(companion === id)}`}
                  >
                    {t(language, key)}
                  </button>
                ))}
              </div>
            </section>

            <section className="py-6">
              <h2 className="mb-1 font-display text-xl text-ink">{t(language, "walkTitle")}</h2>
              <p className="mb-3 text-xs text-ink-soft">{t(language, "walkCaption")}</p>
              <div className="flex flex-wrap gap-2">
                {WALK_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() =>
                      setWalkTags((s) =>
                        s.includes(opt.id)
                          ? s.filter((x) => x !== opt.id)
                          : [...s, opt.id],
                      )
                    }
                    className={`rounded-full border px-4 py-2 text-sm transition ${chip(walkTags.includes(opt.id))}`}
                  >
                    {t(language, opt.labelKey)}
                  </button>
                ))}
              </div>
            </section>
          </div>
        </div>

        <div className="mt-8">
          {loading ? <LoadingState label={t(language, "loadingRoute")} /> : null}
          {error ? (
            <div className="mb-4">
              <ErrorState
                title={t(language, "errorTitle")}
                message={error}
                onRetry={() => void regenerate()}
                retryLabel={t(language, "retry")}
              />
            </div>
          ) : null}

          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={savePrefs}
              className="rounded-full border border-sage-deep bg-sage-deep px-6 py-3.5 text-sm font-medium text-paper transition hover:bg-moss"
            >
              {savedFlash ? t(language, "profileSaved") : t(language, "profileSave")}
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => void regenerate()}
              className="rounded-full border border-line bg-card px-6 py-3.5 text-sm text-ink transition hover:border-sage disabled:opacity-50"
            >
              {t(language, "profileRegenerate")}
            </button>
          </div>

          {!session ? (
            <p className="mt-4 text-sm text-ink-soft">
              {t(language, "profileNoRouteHint")}{" "}
              <Link
                to="/preferences"
                className="text-sage-deep underline-offset-2 hover:underline"
              >
                {t(language, "profileCreateRoute")}
              </Link>
            </p>
          ) : null}
        </div>
      </div>
    </main>
  );
}
