import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  fetchLiveTravelAdvice,
  listPois,
  matchRoutes,
  parseIntent,
  type LiveTravelAdviceResponse,
} from "@/api/client";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { ErrorState, LoadingState } from "@/components/common/States";
import { PreferenceGuideChat } from "@/components/preference/PreferenceGuideChat";
import { TripDaysStepper } from "@/components/preference/TripDaysStepper";
import { StoryChoiceSection } from "@/features/story/components/StoryChoiceSection";
import type { StoryId } from "@/features/story/components/StoryChoiceSection";
import { t } from "@/i18n";
import {
  applyPreferenceToForm,
  changedFormKeys,
  durationLabelKey,
  todayIso,
  toPreference,
  TRIP_DAYS_DEFAULT,
  type PreferenceFormState,
  type ThemeTag,
  type WalkTag,
} from "@/lib/preference";
import { PORT_OPTIONS, portLabel } from "@/lib/ports";
import { useAuth } from "@/state/AuthContext";
import { useWalk } from "@/state/WalkContext";
import type { Preference } from "@/types";
import type { StorySelection } from "@/types";

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
  const { isAuthenticated, savePreference } = useAuth();
  const { language, saveMatch } = useWalk();
  const [duration, setDuration] = useState<PreferenceFormState["duration"]>("half");
  const [tripDays, setTripDays] = useState(TRIP_DAYS_DEFAULT);
  const [interests, setInterests] = useState<string[]>([]);
  const [themes, setThemes] = useState<ThemeTag[]>([]);
  const [companion, setCompanion] = useState<PreferenceFormState["companion"]>("solo");
  const [walkTags, setWalkTags] = useState<WalkTag[]>([]);
  const [entryPort, setEntryPort] = useState<string | null>(null);
  const [exitPort, setExitPort] = useState<string | null>(null);
  const [travelDate, setTravelDate] = useState(() => todayIso());
  const [storyOptIn, setStoryOptIn] = useState<boolean | null>(null);
  const [storyId, setStoryId] = useState<StoryId | null>(null);
  const [storyDay, setStoryDay] = useState<number | null>(null);
  const [storySelections, setStorySelections] = useState<StorySelection[]>([]);
  const [customNote, setCustomNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveAdvice, setLiveAdvice] = useState<LiveTravelAdviceResponse | null>(null);
  const [liveAdviceLoading, setLiveAdviceLoading] = useState(false);
  const [liveAdviceError, setLiveAdviceError] = useState<string | null>(null);
  const [flash, setFlash] = useState<Set<string>>(new Set());
  const [showAdjusters, setShowAdjusters] = useState(false);
  const adjustersRef = useRef<HTMLDivElement>(null);
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
    travelDate,
    storyOptIn: null,
    storyId: null,
    storyDay: null,
    storySelections: [],
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
      travelDate,
      storyOptIn,
      storyId,
      storyDay,
      storySelections,
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
    travelDate,
    storyOptIn,
    storyId,
    storyDay,
    storySelections,
  ]);

  useEffect(() => {
    let cancelled = false;
    setLiveAdviceLoading(true);
    setLiveAdviceError(null);
    void fetchLiveTravelAdvice({
      travelDate,
      tripDays: duration === "multi" ? tripDays : 1,
      language,
    })
      .then((advice) => {
        if (!cancelled) setLiveAdvice(advice);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : t(language, "weatherUnavailable");
        setLiveAdvice(null);
        setLiveAdviceError(
          message.includes("Failed to fetch") ? t(language, "backendDown") : message,
        );
      })
      .finally(() => {
        if (!cancelled) setLiveAdviceLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [duration, language, travelDate, tripDays]);

  useEffect(() => {
    if (flash.size === 0) return;
    const timer = window.setTimeout(() => setFlash(new Set()), 1400);
    return () => window.clearTimeout(timer);
  }, [flash]);

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
    setTravelDate(snapshot.travelDate || todayIso());
    setStoryOptIn(snapshot.storyOptIn);
    setStoryId(snapshot.storyId ?? null);
    setStoryDay(snapshot.storyDay);
    setStorySelections(snapshot.storySelections ?? []);
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
    travelDate: formRef.current.travelDate ?? travelDate,
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
    setTravelDate(next.travelDate || travelDate);
    setStoryOptIn(next.storyOptIn);
    setStoryId(next.storyId ?? null);
    setStoryDay(next.storyDay);
    setStorySelections(next.storySelections ?? []);
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
    const nextStoryDay = formRef.current.storyDay && formRef.current.storyDay <= n
      ? formRef.current.storyDay
      : null;
    const nextSelections = (formRef.current.storySelections ?? []).filter(
      (selection) => selection.story_day <= n,
    );
    formRef.current = {
      ...formRef.current,
      tripDays: n,
      storyDay: nextStoryDay,
      storySelections: nextSelections,
    };
    setTripDays(n);
    setStoryDay(nextStoryDay);
    setStorySelections(nextSelections);
  };

  const selectTravelDate = (value: string) => {
    const next = value || todayIso();
    formRef.current = { ...formRef.current, travelDate: next };
    setTravelDate(next);
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
    if (storyOptIn === null) {
      setError(language === "en" ? "Please choose whether to join a story." : language === "pt" ? "Escolha se pretende participar numa história." : language === "zh-TW" ? "請選擇是否參加故事體驗。" : "请选择是否参加故事体验。");
      return;
    }
    if (storyOptIn && !storyId && storySelections.length === 0) {
      setError(language === "en" ? "Please choose a story." : language === "pt" ? "Escolha uma história." : language === "zh-TW" ? "請選擇一條故事線。" : "请选择一条故事线。");
      return;
    }
    if (storyOptIn && duration === "multi" && storySelections.length === 0) {
      setError(language === "en" ? "Please choose which day includes the story." : language === "pt" ? "Escolha o dia da história." : language === "zh-TW" ? "請選擇故事安排在第幾天。" : "请选择故事安排在第几天。");
      return;
    }
    setLoading(true);
    try {
      const snapshot = formSnapshot();
      const preference = toPreference(snapshot);

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
          if (parsed.preference.story_opt_in !== undefined) {
            preference.story_opt_in = parsed.preference.story_opt_in;
          }
          if (parsed.preference.story_id) preference.story_id = parsed.preference.story_id;
          if (parsed.preference.story_day) preference.story_day = parsed.preference.story_day;
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
      if (isAuthenticated) await savePreference(matchRes.preference);
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

        <TravelDateLiveAdvice
          travelDate={travelDate}
          disabled={loading}
          onChange={selectTravelDate}
          advice={liveAdvice}
          loading={liveAdviceLoading}
          error={liveAdviceError}
          language={language}
        />

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

            <StoryChoiceSection
              language={language}
              multiDay={duration === "multi"}
              tripDays={tripDays}
              arrivalDate={travelDate}
              storyOptIn={storyOptIn}
              storyId={storyId}
              storyDay={storyDay}
              storySelections={duration === "multi" ? storySelections : undefined}
              disabled={loading}
              onDecline={() => {
                formRef.current = { ...formRef.current, storyOptIn: false, storyId: null, storyDay: null, storySelections: [] };
                setStoryOptIn(false);
                setStoryId(null);
                setStoryDay(null);
                setStorySelections([]);
              }}
              onSelectStory={(nextStoryId) => {
                if (duration === "multi") {
                  const current = formRef.current.storySelections ?? [];
                  const existing = current.find((selection) => selection.story_id === nextStoryId);
                  const nextSelections = existing
                    ? current.filter((selection) => selection.story_id !== nextStoryId)
                    : [
                        ...current,
                        {
                          story_id: nextStoryId,
                          story_day:
                            Array.from({ length: tripDays }, (_, index) => index + 1).find(
                              (day) => !current.some((selection) => selection.story_day === day),
                            ) ?? 1,
                        },
                      ];
                  const primary = nextSelections[0] ?? null;
                  formRef.current = {
                    ...formRef.current,
                    storyOptIn: nextSelections.length > 0 ? true : false,
                    storyId: primary?.story_id ?? null,
                    storyDay: primary?.story_day ?? null,
                    storySelections: nextSelections,
                  };
                  setStoryOptIn(nextSelections.length > 0 ? true : false);
                  setStoryId(primary?.story_id ?? null);
                  setStoryDay(primary?.story_day ?? null);
                  setStorySelections(nextSelections);
                  return;
                }
                formRef.current = { ...formRef.current, storyOptIn: true, storyId: nextStoryId, storyDay: 1, storySelections: [{ story_id: nextStoryId, story_day: 1 }] };
                setStoryOptIn(true);
                setStoryId(nextStoryId);
                setStoryDay(1);
                setStorySelections([{ story_id: nextStoryId, story_day: 1 }]);
              }}
              onDayChange={(day) => {
                formRef.current = { ...formRef.current, storyDay: day };
                setStoryDay(day);
              }}
              onStoryDayChange={(nextStoryId, day) => {
                if (!day) return;
                const nextSelections = (formRef.current.storySelections ?? []).map((selection) =>
                  selection.story_id === nextStoryId
                    ? { ...selection, story_day: day }
                    : selection,
                ).filter((selection, index, selections) =>
                  selection.story_id === nextStoryId ||
                  selections.findIndex((candidate) => candidate.story_day === selection.story_day) === index,
                );
                const primary = nextSelections[0] ?? null;
                formRef.current = {
                  ...formRef.current,
                  storyId: primary?.story_id ?? null,
                  storyDay: primary?.story_day ?? null,
                  storySelections: nextSelections,
                };
                setStoryId(primary?.story_id ?? null);
                setStoryDay(primary?.story_day ?? null);
                setStorySelections(nextSelections);
              }}
            />

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

function TravelDateLiveAdvice({
  travelDate,
  disabled,
  onChange,
  advice,
  loading,
  error,
  language,
}: {
  travelDate: string;
  disabled: boolean;
  onChange: (value: string) => void;
  advice: LiveTravelAdviceResponse | null;
  loading: boolean;
  error: string | null;
  language: PreferenceFormState["language"];
}) {
  return (
    <section className="mb-10">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="font-display text-xl text-ink">{t(language, "weatherTitle")}</h2>
        <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-ink-soft">
          {t(language, "weatherCaption")}
        </span>
      </div>
      <div className="rounded-2xl border border-line bg-card p-5">
        <label className="block">
          <span className="mb-2 block text-xs font-medium text-ink">
            {t(language, "travelDateLabel")}
          </span>
          <input
            type="date"
            value={travelDate}
            min={todayIso()}
            disabled={disabled}
            onChange={(event) => onChange(event.target.value)}
            className="h-11 w-full rounded-xl border border-line bg-paper px-4 text-sm text-ink outline-none focus:border-sage-deep sm:max-w-xs"
          />
        </label>
        <p className="mt-2 text-xs text-ink-soft">{t(language, "travelDateHint")}</p>
        <LiveAdvicePanel advice={advice} loading={loading} error={error} language={language} />
      </div>
    </section>
  );
}

function LiveAdvicePanel({
  advice,
  loading,
  error,
  language,
}: {
  advice: LiveTravelAdviceResponse | null;
  loading: boolean;
  error: string | null;
  language: PreferenceFormState["language"];
}) {
  if (loading) {
    return (
      <div className="mt-4 rounded-xl border border-line bg-paper-warm px-4 py-3 text-sm text-ink-soft">
        {t(language, "liveAdviceLoading")}
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-4 rounded-xl border border-clay/30 bg-clay/5 px-4 py-3 text-sm text-clay">
        {t(language, "weatherUnavailable")} · {error}
      </div>
    );
  }

  if (!advice) return null;

  const firstDay = advice.weather.days[0];
  const temp =
    firstDay?.temperature_min_c != null && firstDay.temperature_max_c != null
      ? `${Math.round(firstDay.temperature_min_c)}-${Math.round(firstDay.temperature_max_c)}°C`
      : null;
  const rain =
    firstDay?.precipitation_probability_percent != null
      ? `${Math.round(firstDay.precipitation_probability_percent)}%`
      : null;
  const changedRoutes = advice.transport.alerts?.map((item) => item.route) ?? [];
  const transportNote = changedRoutes.length
    ? {
        "zh-CN": `交通事务局实时资料显示 ${changedRoutes.length} 条线路有调整：${changedRoutes.slice(0, 8).join("、")}。请在出发前展开对应线路确认暂停站点。`,
        "zh-TW": `交通事務局即時資料顯示 ${changedRoutes.length} 條路線有調整：${changedRoutes.slice(0, 8).join("、")}。請在出發前展開對應路線確認暫停站點。`,
        en: `Live DSAT data shows changes on ${changedRoutes.length} routes: ${changedRoutes.slice(0, 8).join(", ")}. Check the relevant route before departure.`,
        pt: `Os dados em tempo real da DSAT indicam alterações em ${changedRoutes.length} carreiras: ${changedRoutes.slice(0, 8).join(", ")}. Confirme a carreira antes de partir.`,
      }[language]
    : advice.transport.notes[0];

  return (
    <div className="mt-4 rounded-2xl border border-sage/30 bg-sage/5 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-medium text-ink">{advice.weather.summary}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-ink-soft">
            {temp ? (
              <span className="rounded-full bg-paper px-3 py-1">
                {t(language, "weatherTempRange")}: {temp}
              </span>
            ) : null}
            {rain ? (
              <span className="rounded-full bg-paper px-3 py-1">
                {t(language, "weatherRainChance")}: {rain}
              </span>
            ) : null}
            {firstDay?.condition ? (
              <span className="rounded-full bg-paper px-3 py-1">
                {t(language, "weatherForecast")}: {firstDay.condition}
              </span>
            ) : null}
          </div>
        </div>
        <div className="flex gap-2 text-lg" aria-hidden>
          {advice.weather.flags.umbrella ? <span>☂</span> : null}
          {advice.weather.flags.sunscreen ? <span>☀</span> : null}
          {advice.weather.flags.indoor_backup ? <span>⌂</span> : null}
        </div>
      </div>

      {advice.weather.advice.length ? (
        <ul className="mt-3 space-y-1.5 text-xs leading-relaxed text-ink">
          {advice.weather.advice.map((item) => (
            <li key={item}>• {item}</li>
          ))}
        </ul>
      ) : null}

      {advice.weather.source?.name ? (
        <p className="mt-3 text-[10px] text-ink-soft">
          {t(language, "weatherSource")}: {advice.weather.source.name}
          {advice.weather.source.issued_at
            ? ` · ${t(language, "weatherIssuedAt")}: ${advice.weather.source.issued_at}`
            : ""}
        </p>
      ) : null}

      {advice.crowd.level !== "low" ? (
        <div className="mt-4 border-t border-sage/20 pt-4">
          <p className="text-sm font-medium text-ink">
            {t(language, "crowdForecastTitle")} · {t(language, crowdLevelKey(advice.crowd.level))}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-ink-soft">
            {t(language, "crowdForecastNotice")}
          </p>
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 border-t border-sage/20 pt-4 sm:grid-cols-2">
        <OfficialLinkPanel
          title={t(language, "transportTitle")}
          note={transportNote}
          source={advice.transport.sources[0]}
          language={language}
        />
        <OfficialLinkPanel
          title={t(language, "openingHoursTitle")}
          note={advice.opening_hours.notes[0]}
          language={language}
        />
      </div>
    </div>
  );
}

function crowdLevelKey(level: string): "crowdMedium" | "crowdHigh" | "crowdVeryHigh" {
  if (level === "very_high") return "crowdVeryHigh";
  if (level === "high") return "crowdHigh";
  return "crowdMedium";
}

function OfficialLinkPanel({
  title,
  note,
  source,
  language,
}: {
  title: string;
  note?: string;
  source?: { name: string; url: string };
  language: PreferenceFormState["language"];
}) {
  return (
    <div className="rounded-xl border border-line/80 bg-paper/70 p-3">
      <p className="text-xs font-medium text-ink">{title}</p>
      {note ? <p className="mt-1 text-[11px] leading-relaxed text-ink-soft">{note}</p> : null}
      {source ? (
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="mt-2 inline-flex text-[11px] font-medium text-sage-deep underline underline-offset-2"
        >
          {t(language, "officialSource")}: {source.name}
        </a>
      ) : null}
    </div>
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
