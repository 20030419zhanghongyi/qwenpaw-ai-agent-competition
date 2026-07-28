import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listPois, matchRoutes, parseIntent } from "@/api/client";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { ErrorState, LoadingState } from "@/components/common/States";
import { PreferenceGuideChat } from "@/components/preference/PreferenceGuideChat";
import { TripDaysStepper } from "@/components/preference/TripDaysStepper";
import { StoryInvitationCard } from "@/features/story/components/StoryInvitationCard";
import { t } from "@/i18n";
import {
  applyPreferenceToForm,
  changedFormKeys,
  durationLabelKey,
  toPreference,
  TRIP_DAYS_DEFAULT,
  type PreferenceFormState,
  type ThemeTag,
  type WalkTag,
} from "@/lib/preference";
import { PORT_OPTIONS, portLabel } from "@/lib/ports";
import { useWalk } from "@/state/WalkContext";
import type { Preference } from "@/types";
import { matchStory } from "@/story-discovery/storyMatcher";
import {
  hasActiveInvitationSuppression,
  markInvitationAccepted,
  markInvitationDeclined,
} from "@/story-discovery/invitationState";
import type { StoryDiscoveryPreference, StoryMatchResult } from "@/story-discovery/types";

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
  hintKey:
    | "walkLessHint"
    | "walkNoBacktrackHint"
    | "walkShadeHint"
    | "walkFlatHint"
    | "walkIndoorHint"
    | "walkAccessibleHint";
}> = [
  { id: "less-walk", labelKey: "walkLess", hintKey: "walkLessHint" },
  { id: "no-backtrack", labelKey: "walkNoBacktrack", hintKey: "walkNoBacktrackHint" },
  { id: "shade", labelKey: "walkShade", hintKey: "walkShadeHint" },
  { id: "flat", labelKey: "walkFlat", hintKey: "walkFlatHint" },
  { id: "indoor", labelKey: "walkIndoor", hintKey: "walkIndoorHint" },
  { id: "accessible", labelKey: "walkAccessible", hintKey: "walkAccessibleHint" },
];

export function PreferencePage() {
  const navigate = useNavigate();
  const { language, saveMatch } = useWalk();
  const [duration, setDuration] = useState<PreferenceFormState["duration"]>("half");
  const [tripDays, setTripDays] = useState(TRIP_DAYS_DEFAULT);
  const [interests, setInterests] = useState<string[]>([]);
  const [themes, setThemes] = useState<ThemeTag[]>([]);
  const [companion, setCompanion] = useState<PreferenceFormState["companion"]>("solo");
  const [walkTags, setWalkTags] = useState<WalkTag[]>([]);
  const [entryPort, setEntryPort] = useState<string | null>(null);
  const [exitPort, setExitPort] = useState<string | null>(null);
  const [customNote, setCustomNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [storyInvitation, setStoryInvitation] = useState<StoryMatchResult | null>(null);
  const [flash, setFlash] = useState<Set<string>>(new Set());
  const [showAdjusters, setShowAdjusters] = useState(false);
  const adjustersRef = useRef<HTMLDivElement>(null);
  const invitationRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<PreferenceFormState>({
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
  });

  useEffect(() => {
    formRef.current = {
      duration,
      tripDays,
      interests,
      themes,
      companion,
      walkTags,
      customNote,
      language,
      entryPort,
      exitPort,
      travelDate: formRef.current.travelDate,
    };
  }, [
    duration,
    tripDays,
    interests,
    themes,
    companion,
    walkTags,
    customNote,
    language,
    entryPort,
    exitPort,
  ]);

  useEffect(() => {
    if (flash.size === 0) return;
    const timer = window.setTimeout(() => setFlash(new Set()), 1400);
    return () => window.clearTimeout(timer);
  }, [flash]);

  useEffect(() => {
    const match = matchStory({
      duration,
      interests,
      themes,
      walkTags,
    });
    setStoryInvitation((current) => {
      if (match.matched) {
        return hasActiveInvitationSuppression(match.storyId) ? null : match;
      }
      return current;
    });
  }, [duration, interests, themes, walkTags]);

  useEffect(() => {
    if (!showAdjusters) return;
    // 展开时强制用累计回填结果刷一遍，避免对话阶段的 setState 与首屏不同步
    const snapshot = formRef.current;
    setDuration(snapshot.duration);
    setTripDays(snapshot.tripDays);
    setInterests([...snapshot.interests]);
    setThemes([...snapshot.themes]);
    setCompanion(snapshot.companion);
    setWalkTags([...snapshot.walkTags]);
    setEntryPort(snapshot.entryPort);
    setExitPort(snapshot.exitPort);
    adjustersRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [showAdjusters]);

  const revealForm = () => setShowAdjusters(true);

  const formSnapshot = (): PreferenceFormState => ({
    ...formRef.current,
    customNote,
    language,
    // Prefer ref (updated synchronously on chip click) so generate never drops ports.
    entryPort: formRef.current.entryPort ?? entryPort,
    exitPort: formRef.current.exitPort ?? exitPort,
  });

  const applyFromChat = (pref: Preference) => {
    // 用 ref 做增量合并，避免同一次对话里连续回填读到过期 state
    const before = formRef.current;
    const next = applyPreferenceToForm(pref, before);
    formRef.current = next;
    const keys = changedFormKeys(before, next);
    if (keys.length) setFlash(new Set(keys));
    setDuration(next.duration);
    setTripDays(next.tripDays);
    setInterests(next.interests);
    setThemes(next.themes);
    setCompanion(next.companion);
    setWalkTags(next.walkTags);
    setEntryPort(next.entryPort);
    setExitPort(next.exitPort);
  };

  const flashClass = (key: string, active: boolean) =>
    [
      active
        ? "border-sage-deep bg-sage-deep/5 shadow-[var(--shadow-soft)]"
        : "border-line bg-card hover:border-sage",
      flash.has(key) ? "ring-2 ring-ochre ring-offset-2 ring-offset-paper transition" : "transition",
    ].join(" ");

  const selectDuration = (id: PreferenceFormState["duration"]) => {
    formRef.current = { ...formRef.current, duration: id };
    setDuration(id);
  };

  const selectTripDays = (n: number) => {
    formRef.current = { ...formRef.current, tripDays: n };
    setTripDays(n);
  };

  const selectCompanion = (id: PreferenceFormState["companion"]) => {
    formRef.current = { ...formRef.current, companion: id };
    setCompanion(id);
  };

  const toggleInterest = (id: string) =>
    setInterests((s) => {
      const next = s.includes(id) ? s.filter((x) => x !== id) : [...s, id];
      formRef.current = { ...formRef.current, interests: next };
      return next;
    });

  const toggleTheme = (id: ThemeTag) =>
    setThemes((s) => {
      const next = s.includes(id) ? s.filter((x) => x !== id) : [...s, id];
      formRef.current = { ...formRef.current, themes: next };
      return next;
    });

  const toggleWalk = (id: WalkTag) =>
    setWalkTags((s) => {
      const next = s.includes(id) ? s.filter((x) => x !== id) : [...s, id];
      formRef.current = { ...formRef.current, walkTags: next };
      return next;
    });

  const generate = async () => {
    setError(null);
    setLoading(true);
    try {
      const snapshot = formSnapshot();
      const preference = toPreference(snapshot);

      // ── Story Discovery (before parseIntent — uses form state only) ──
      const discoveryPref: StoryDiscoveryPreference = {
        duration: snapshot.duration,
        interests: snapshot.interests,
        themes: snapshot.themes,
        walkTags: snapshot.walkTags,
      };
      const storyMatch = matchStory(discoveryPref);
      const suppressed = hasActiveInvitationSuppression(storyMatch.storyId);

      if (storyMatch.matched && !suppressed) {
        setStoryInvitation(storyMatch);
        window.requestAnimationFrame(() =>
          invitationRef.current?.scrollIntoView({
            behavior: "smooth",
            block: "center",
          }),
        );
        return;
      }

      if (customNote.trim()) {
        try {
          const parsed = await parseIntent(customNote.trim());
          preference.physical = [
            ...new Set([...(preference.physical ?? []), ...(parsed.preference.physical ?? [])]),
          ];
          preference.interests = [
            ...new Set([...(preference.interests ?? []), ...(parsed.preference.interests ?? [])]),
          ];
          if (parsed.preference.travel_type?.length) {
            preference.travel_type = [
              ...new Set([
                ...(preference.travel_type ?? []),
                ...parsed.preference.travel_type,
              ]),
            ];
          }
          if (parsed.preference.duration) {
            preference.duration = parsed.preference.duration;
          }
          if (typeof parsed.preference.trip_days === "number") {
            preference.trip_days = parsed.preference.trip_days;
          }
          if (parsed.preference.entry_port) {
            preference.entry_port = parsed.preference.entry_port;
          }
          if (parsed.preference.exit_port) {
            preference.exit_port = parsed.preference.exit_port;
          }
          if (parsed.preference.travel_date) {
            preference.travel_date = parsed.preference.travel_date;
          }
        } catch {
          // chips still work
        }
      }

      await executeRouteMatch(preference);
    } catch (err) {
      const message = err instanceof Error ? err.message : "request failed";
      setError(
        message.includes("Failed to fetch") ? t(language, "backendDown") : message,
      );
    } finally {
      setLoading(false);
    }
  };

  // ── Extracted route-matching (also called by decline / accept-fallback) ──

  const executeRouteMatch = async (preference: Preference) => {
    setLoading(true);
    try {
      const [matchRes, pois] = await Promise.all([
        matchRoutes(preference),
        listPois({ limit: 500 }),
      ]);
      const top = matchRes.matches[0];
      if (!top) {
        throw new Error(t(language, "noMatch"));
      }
      const isMulti = preference.duration === "multi-day" || duration === "multi";
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

  // ── Story invitation handlers ───────────────────────────────────────────

  const handleStoryAccept = () => {
    if (!storyInvitation) return;

    const coverPath = `/stories/${storyInvitation.storyId}`;
    markInvitationAccepted(storyInvitation.storyId);
    setStoryInvitation(null);
    navigate(coverPath);
  };

  const handleStoryDecline = () => {
    if (!storyInvitation) return;
    markInvitationDeclined(storyInvitation.storyId);
    setStoryInvitation(null);
  };

  return (
    <>
    <main className="min-h-screen bg-paper pb-32">
      <header className="sticky top-14 z-20 flex items-center justify-between border-b border-line/70 bg-paper/95 px-5 py-4 backdrop-blur lg:px-12">
        <Link to="/guide" className="text-sm text-ink-soft hover:text-ink">
          {t(language, "back")}
        </Link>
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
          {t(language, "chapterII")}
        </p>
        <Link to="/profile" className="text-sm text-ink-soft hover:text-ink">
          {t(language, "navProfile")}
        </Link>
      </header>

      <div className="mx-auto max-w-3xl px-5 pt-8 lg:px-0">
        <h1 className="mb-2 font-display text-3xl leading-tight text-ink lg:text-4xl">
          {t(language, "prefTitle")}
          <br />
          <span className="italic text-sage-deep">{t(language, "prefTitleAccent")}</span>
        </h1>
        <p className="mb-10 max-w-lg text-sm leading-relaxed text-ink-soft">
          {t(language, "prefLead")}
        </p>

        <AzulejoBand className="mb-10" />

        <PreferenceGuideChat
          language={language}
          disabled={loading}
          formVisible={showAdjusters}
          onApplyPreference={applyFromChat}
          onReadyChange={(ready) => {
            if (ready) setShowAdjusters(true);
          }}
          onRevealForm={revealForm}
        />

        {loading ? <LoadingState label={t(language, "loadingRoute")} /> : null}
        {error ? (
          <div className="mb-8">
            <ErrorState
              title={t(language, "errorTitle")}
              message={error}
              onRetry={generate}
              retryLabel={t(language, "retry")}
            />
          </div>
        ) : null}

        {!showAdjusters ? (
          <p className="mb-8 text-center text-xs text-ink-soft">{t(language, "chatFirstHint")}</p>
        ) : (
          <div ref={adjustersRef} className="animate-[fadeIn_0.45s_ease]">
            <div className="mb-8">
              <h2 className="font-display text-2xl text-ink">{t(language, "adjustTitle")}</h2>
              <p className="mt-1 text-sm text-ink-soft">{t(language, "adjustLead")}</p>
            </div>

            <Section title={t(language, "durationTitle")} caption={t(language, "durationCaption")}>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {(
                  [
                    {
                      id: "half" as const,
                      title: t(language, "durationHalf"),
                      sub: t(language, "durationHalfSub"),
                      desc: t(language, "durationHalfDesc"),
                    },
                    {
                      id: "full" as const,
                      title: t(language, "durationFull"),
                      sub: t(language, "durationFullSub"),
                      desc: t(language, "durationFullDesc"),
                    },
                    {
                      id: "night" as const,
                      title: t(language, "durationNight"),
                      sub: t(language, "durationNightSub"),
                      desc: t(language, "durationNightDesc"),
                    },
                    {
                      id: "multi" as const,
                      title: t(language, "durationMulti"),
                      sub: t(language, "durationMultiSub"),
                      desc: t(language, "durationMultiDesc"),
                    },
                  ] as const
                ).map((d) => {
                  const active = duration === d.id;
                  return (
                    <button
                      key={d.id}
                      type="button"
                      disabled={loading}
                      onClick={() => selectDuration(d.id)}
                      className={`rounded-2xl border p-5 text-left ${flashClass(`duration:${d.id}`, active)}`}
                    >
                      <p className="font-display text-xl text-ink">{d.title}</p>
                      <p className="mt-0.5 text-[11px] uppercase tracking-widest text-sage-deep">
                        {d.sub}
                      </p>
                      <p className="mt-3 text-xs text-ink-soft">{d.desc}</p>
                    </button>
                  );
                })}
              </div>
              {duration === "multi" ? (
                <TripDaysStepper
                  language={language}
                  value={tripDays}
                  disabled={loading}
                  highlighted={flash.has("tripDays")}
                  onChange={selectTripDays}
                />
              ) : null}
            </Section>

            <Section title={t(language, "portsTitle")} caption={t(language, "portsCaption")}>
              <div className="space-y-4">
                <div>
                  <p className="mb-2 text-xs font-medium text-ink">{t(language, "entryPortLabel")}</p>
                  <div className="flex flex-wrap gap-2.5">
                    {PORT_OPTIONS.map((port) => {
                      const active = entryPort === port.poiId;
                      return (
                        <button
                          key={`entry-${port.poiId}`}
                          type="button"
                          disabled={loading}
                          onClick={() => {
                            const next = active ? null : port.poiId;
                            formRef.current = { ...formRef.current, entryPort: next };
                            setEntryPort(next);
                          }}
                          className={`rounded-full border px-4 py-2 text-sm transition ${flashClass(
                            `entryPort:${port.poiId}`,
                            active,
                          )}`}
                        >
                          {portLabel(port.poiId, language)}
                        </button>
                      );
                    })}
                  </div>
                </div>
                <div>
                  <p className="mb-2 text-xs font-medium text-ink">{t(language, "exitPortLabel")}</p>
                  <div className="flex flex-wrap gap-2.5">
                    {PORT_OPTIONS.map((port) => {
                      const active = exitPort === port.poiId;
                      return (
                        <button
                          key={`exit-${port.poiId}`}
                          type="button"
                          disabled={loading}
                          onClick={() => {
                            const next = active ? null : port.poiId;
                            formRef.current = { ...formRef.current, exitPort: next };
                            setExitPort(next);
                          }}
                          className={`rounded-full border px-4 py-2 text-sm transition ${flashClass(
                            `exitPort:${port.poiId}`,
                            active,
                          )}`}
                        >
                          {portLabel(port.poiId, language)}
                        </button>
                      );
                    })}
                  </div>
                </div>
                {!entryPort || !exitPort ? (
                  <p className="text-xs text-ink-soft">{t(language, "portsOptionalHint")}</p>
                ) : null}
              </div>
            </Section>

            <Section title={t(language, "themesTitle")} caption={t(language, "themesCaption")}>
              <div className="flex flex-wrap gap-2.5">
                {THEME_OPTIONS.map((opt) => {
                  const active = themes.includes(opt.id);
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      disabled={loading}
                      onClick={() => toggleTheme(opt.id)}
                      className={`rounded-full border px-5 py-2.5 text-sm ${
                        active
                          ? `border-sage-deep bg-sage-deep text-paper ${flash.has(`theme:${opt.id}`) ? "ring-2 ring-ochre ring-offset-2 ring-offset-paper" : ""}`
                          : "border-line bg-card text-ink hover:border-sage"
                      }`}
                    >
                      {t(language, opt.labelKey)}
                    </button>
                  );
                })}
              </div>
              <p className="mt-3 text-[11px] leading-relaxed text-ink-soft">
                {t(language, "themeCotaiHint")}
              </p>
            </Section>

            <Section
              title={t(language, "interestsTitle")}
              caption={t(language, "interestsCaption")}
            >
              <div className="flex flex-wrap gap-2.5">
                {(
                  [
                    ["history", "interestHistory"],
                    ["arch", "interestArch"],
                    ["food", "interestFood"],
                    ["photo", "interestPhoto"],
                    ["culture", "interestCulture"],
                    ["relax", "interestRelax"],
                  ] as const
                ).map(([id, key]) => {
                  const active = interests.includes(id);
                  return (
                    <button
                      key={id}
                      type="button"
                      disabled={loading}
                      onClick={() => toggleInterest(id)}
                      className={`rounded-full border px-5 py-2.5 text-sm ${
                        active
                          ? `border-sage-deep bg-sage-deep text-paper ${flash.has(`interest:${id}`) ? "ring-2 ring-ochre ring-offset-2 ring-offset-paper" : ""}`
                          : "border-line bg-card text-ink hover:border-sage"
                      }`}
                    >
                      {t(language, key)}
                    </button>
                  );
                })}
              </div>
            </Section>

            {storyInvitation && (
              <div ref={invitationRef}>
                <StoryInvitationCard
                  onAccept={handleStoryAccept}
                  onDecline={handleStoryDecline}
                />
              </div>
            )}

            <Section
              title={t(language, "companionTitle")}
              caption={t(language, "companionCaption")}
            >
              <div className="grid grid-cols-3 gap-3">
                {(
                  [
                    ["solo", "companionSolo", "☂"],
                    ["friends", "companionFriends", "◎"],
                    ["family", "companionFamily", "❁"],
                  ] as const
                ).map(([id, key, icon]) => {
                  const active = companion === id;
                  return (
                    <button
                      key={id}
                      type="button"
                      disabled={loading}
                      onClick={() => selectCompanion(id)}
                      className={`flex flex-col items-center gap-2 rounded-2xl border py-5 ${flashClass(`companion:${id}`, active)}`}
                    >
                      <span className="text-2xl text-sage-deep">{icon}</span>
                      <span className="text-sm font-medium text-ink">{t(language, key)}</span>
                    </button>
                  );
                })}
              </div>
            </Section>

            <Section title={t(language, "walkTitle")} caption={t(language, "walkCaption")}>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {WALK_OPTIONS.map((opt) => {
                  const active = walkTags.includes(opt.id);
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      disabled={loading}
                      onClick={() => toggleWalk(opt.id)}
                      className={`rounded-2xl border px-4 py-3.5 text-left ${flashClass(`walk:${opt.id}`, active)}`}
                    >
                      <p className="text-sm font-medium text-ink">{t(language, opt.labelKey)}</p>
                      <p className="mt-0.5 text-xs text-ink-soft">{t(language, opt.hintKey)}</p>
                    </button>
                  );
                })}
              </div>
              <div className="mt-4">
                <p className="mb-2 text-xs font-medium text-ink-soft">{t(language, "walkCustom")}</p>
                <input
                  value={customNote}
                  onChange={(e) => setCustomNote(e.target.value)}
                  disabled={loading}
                  placeholder={t(language, "walkCustomPlaceholder")}
                  className="w-full rounded-xl border border-line bg-card px-4 py-3 text-sm text-ink outline-none ring-sage focus:ring-2"
                />
              </div>
            </Section>
          </div>
        )}
      </div>

      {showAdjusters ? (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-line/70 bg-paper/95 px-5 py-4 backdrop-blur lg:px-12">
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-4">
            <div className="hidden text-xs text-ink-soft sm:block">
              {t(language, "selectedSummary")} · {t(language, durationLabelKey(duration))}
              {duration === "multi"
                ? ` · ${t(language, "tripDaysPlay").replace("{n}", String(tripDays))}`
                : null}
              <span className="mx-2 text-line">·</span>
              {interests.length} {t(language, "interestsCount")}
            </div>
            <button
              type="button"
              disabled={loading}
              onClick={generate}
              className="w-full rounded-full bg-sage-deep px-6 py-3.5 font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto sm:px-10"
            >
              {loading ? t(language, "generating") : t(language, "generateRoute")}
            </button>
          </div>
        </div>
      ) : null}
    </main>

    </>
  );
}

function Section({
  title,
  caption,
  children,
}: {
  title: string;
  caption: string;
  children: ReactNode;
}) {
  return (
    <section className="mb-10">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="font-display text-xl text-ink">{title}</h2>
        <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-ink-soft">
          {caption}
        </span>
      </div>
      {children}
    </section>
  );
}
