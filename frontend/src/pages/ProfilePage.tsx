import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listPois, matchRoutes } from "@/api/client";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { ErrorState, LoadingState } from "@/components/common/States";
import { TripDaysStepper } from "@/components/preference/TripDaysStepper";
import { ProfileSidebar } from "@/components/profile/ProfileSidebar";
import { t } from "@/i18n";
import { getLastTripId } from "@/lib/lastTrip";
import {
  applyPreferenceToForm,
  toPreference,
  TRIP_DAYS_DEFAULT,
  type PreferenceFormState,
  type ThemeTag,
  type WalkTag,
} from "@/lib/preference";
import { PORT_OPTIONS, portLabel } from "@/lib/ports";
import { useAuth } from "@/state/AuthContext";
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
  tripDays: TRIP_DAYS_DEFAULT,
  interests: [],
  themes: [],
  companion: "solo",
  walkTags: [],
  customNote: "",
  language,
  entryPort: null,
  exitPort: null,
  travelDate: null,
  storyOptIn: null,
  storyId: null,
  storyDay: null,
});

export function ProfilePage() {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();
  const { language, setLanguage, preference, session, updatePreference, saveMatch } =
    useWalk();
  const [duration, setDuration] = useState<PreferenceFormState["duration"]>("half");
  const [tripDays, setTripDays] = useState(TRIP_DAYS_DEFAULT);
  const [interests, setInterests] = useState<string[]>([]);
  const [themes, setThemes] = useState<ThemeTag[]>([]);
  const [companion, setCompanion] = useState<PreferenceFormState["companion"]>("solo");
  const [walkTags, setWalkTags] = useState<WalkTag[]>([]);
  const [entryPort, setEntryPort] = useState<string | null>(null);
  const [exitPort, setExitPort] = useState<string | null>(null);
  const [savedFlash, setSavedFlash] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<PreferenceFormState>(emptyForm(language));
  const postcardTripId = getLastTripId();

  useEffect(() => {
    formRef.current = {
      duration,
      tripDays,
      interests,
      themes,
      companion,
      walkTags,
      customNote: "",
      language,
      entryPort,
      exitPort,
      travelDate: preference?.travel_date ?? null,
      storyOptIn: preference?.story_opt_in ?? null,
      storyId: preference?.story_id ?? null,
      storyDay: preference?.story_day ?? null,
    };
  }, [
    duration,
    tripDays,
    interests,
    themes,
    companion,
    walkTags,
    language,
    entryPort,
    exitPort,
    preference?.travel_date,
  ]);

  useEffect(() => {
    if (!preference) {
      const cleared = emptyForm(language);
      formRef.current = cleared;
      setDuration(cleared.duration);
      setTripDays(cleared.tripDays);
      setInterests(cleared.interests);
      setThemes(cleared.themes);
      setCompanion(cleared.companion);
      setWalkTags(cleared.walkTags);
      setEntryPort(cleared.entryPort);
      setExitPort(cleared.exitPort);
      return;
    }
    // Merge onto the live editor (via formRef), not emptyForm. emptyForm always
    // starts at duration=half / tripDays=3, so applyPreferenceToForm treated every
    // multi-day preference without trip_days as a fresh multi switch and reset
    // the stepper to 3 — wiping an in-progress day count before regenerate.
    const form = applyPreferenceToForm(preference, formRef.current);
    formRef.current = form;
    setDuration(form.duration);
    setTripDays(form.tripDays);
    setInterests(form.interests);
    setThemes(form.themes);
    setCompanion(form.companion);
    setWalkTags(form.walkTags);
    setEntryPort(form.entryPort);
    setExitPort(form.exitPort);
  }, [preference, language]);

  const snapshot = (): PreferenceFormState => ({
    duration,
    tripDays,
    interests,
    themes,
    companion,
    walkTags,
    customNote: "",
    language,
    entryPort,
    exitPort,
    travelDate: preference?.travel_date ?? null,
    storyOptIn: preference?.story_opt_in ?? null,
    storyId: preference?.story_id ?? null,
    storyDay: preference?.story_day ?? null,
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
      <div className="relative mx-auto max-w-6xl px-5 pt-8 lg:px-8">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
          {t(language, "profileEyebrow")}
        </p>
        <h1 className="mb-2 font-display text-3xl leading-tight text-ink lg:text-4xl">
          {t(language, "profileTitle")}
        </h1>
        <p className="mb-8 max-w-lg text-sm leading-relaxed text-ink-soft">
          {t(language, "profileLead")}
        </p>

        <div className="grid min-w-0 gap-8 lg:grid-cols-[13rem_minmax(0,1fr)]">
          <ProfileSidebar language={language} />
          <div className="min-w-0">

        <section className="mb-8 rounded-2xl border border-line bg-card px-5 py-4 shadow-[var(--shadow-soft)]">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
            {t(language, "authAccount")}
          </p>
          {isAuthenticated && user ? (
            <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-ink">
                {t(language, "authSignedInAs").replace(
                  "{id}",
                  user.email ?? user.phone ?? user.user_id,
                )}
              </p>
              <button
                type="button"
                onClick={logout}
                className="rounded-full border border-line px-4 py-2 text-sm text-ink transition hover:border-sage"
              >
                {t(language, "authLogout")}
              </button>
            </div>
          ) : (
            <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-ink-soft">{t(language, "authPrompt")}</p>
              <Link
                to="/auth?returnTo=%2Fprofile"
                className="rounded-full bg-sage-deep px-4 py-2 text-sm font-medium text-paper transition hover:bg-moss"
              >
                {t(language, "authLink")}
              </Link>
            </div>
          )}
        </section>

        <AzulejoBand className="mb-8" />

        <section className="mb-8 rounded-2xl border border-line bg-card px-5 py-4 shadow-[var(--shadow-soft)]">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
            {t(language, "profilePostcards")}
          </p>
          <p className="mt-2 text-sm text-ink-soft">{t(language, "profilePostcardsLead")}</p>
          <Link
            to={
              !isAuthenticated && postcardTripId
                ? `/postcards?trip=${encodeURIComponent(postcardTripId)}`
                : "/postcards"
            }
            className="mt-4 inline-flex h-10 items-center rounded-full border border-sage-deep px-4 text-sm font-medium text-sage-deep transition hover:bg-sage-deep hover:text-paper"
          >
            {t(language, "postcardOpenGallery")}
          </Link>
        </section>

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
                    onClick={() => {
                      formRef.current = { ...formRef.current, duration: id };
                      setDuration(id);
                    }}
                    className={`rounded-2xl border px-3 py-3 text-sm transition ${chip(duration === id)}`}
                  >
                    {t(language, key)}
                  </button>
                ))}
              </div>
              {duration === "multi" ? (
                <TripDaysStepper
                  language={language}
                  value={tripDays}
                  onChange={(n) => {
                    formRef.current = { ...formRef.current, tripDays: n };
                    setTripDays(n);
                  }}
                />
              ) : null}
            </section>

            <section className="py-6">
              <h2 className="mb-1 font-display text-xl text-ink">{t(language, "portsTitle")}</h2>
              <p className="mb-3 text-xs text-ink-soft">{t(language, "portsCaption")}</p>
              <div className="space-y-4">
                <div>
                  <p className="mb-2 text-xs font-medium text-ink">{t(language, "entryPortLabel")}</p>
                  <div className="flex flex-wrap gap-2">
                    {PORT_OPTIONS.map((port) => (
                      <button
                        key={`entry-${port.poiId}`}
                        type="button"
                        onClick={() => setEntryPort(entryPort === port.poiId ? null : port.poiId)}
                        className={`rounded-full border px-4 py-2 text-sm transition ${chip(entryPort === port.poiId)}`}
                      >
                        {portLabel(port.poiId, language)}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="mb-2 text-xs font-medium text-ink">{t(language, "exitPortLabel")}</p>
                  <div className="flex flex-wrap gap-2">
                    {PORT_OPTIONS.map((port) => (
                      <button
                        key={`exit-${port.poiId}`}
                        type="button"
                        onClick={() => setExitPort(exitPort === port.poiId ? null : port.poiId)}
                        className={`rounded-full border px-4 py-2 text-sm transition ${chip(exitPort === port.poiId)}`}
                      >
                        {portLabel(port.poiId, language)}
                      </button>
                    ))}
                  </div>
                </div>
                {!entryPort || !exitPort ? (
                  <p className="text-xs text-ink-soft">{t(language, "portsOptionalHint")}</p>
                ) : null}
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
        </div>
      </div>
    </main>
  );
}
