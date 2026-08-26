import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  askGuide,
  generateGuide,
  listPois,
  type GuideGenerateResponse,
} from "@/api/client";
import heroImg from "@/assets/hero-ruins.jpg";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import {
  GuideNarrationSections,
  sectionsFromText,
} from "@/components/guide/GuideNarrationSections";
import { LocalSpeechPlayer } from "@/components/guide/LocalSpeechPlayer";
import { PhotoRecognitionPanel } from "@/components/guide/PhotoRecognitionPanel";
import { t } from "@/i18n";
import { resolvePoiImage, curatedPoiImage } from "@/lib/poiImage";
import { getLastTripId } from "@/lib/lastTrip";
import { useAuth } from "@/state/AuthContext";
import { useTrip } from "@/state/TripContext";
import { localizedPoiMeta, localizedPoiName, localizedPoiSearchText } from "@/lib/poiLocalization";
import { useWalk } from "@/state/WalkContext";
import type { POI } from "@/types";

interface ChatTurn {
  role: "user" | "assistant";
  text: string;
  webUsed?: boolean;
  webSources?: Array<{ title?: string; url?: string; source?: string }>;
}

export function GuidePage() {
  const { language, preference, session } = useWalk();
  const { token } = useAuth();
  const { trip } = useTrip();
  const [searchParams, setSearchParams] = useSearchParams();
  const deepPoi = searchParams.get("poi") ?? "";
  const deepName = searchParams.get("name") ?? "";
  const fromWalk = searchParams.get("from") === "walk";
  const nextStopParam = searchParams.has("next") ? (searchParams.get("next") ?? "") : null;
  const nextStopId = searchParams.get("nextId") ?? "";

  const sessionNext = useMemo(() => {
    const route = session?.match?.route;
    const poisById = session?.poisById ?? {};
    if (!route?.nodes?.length) return null;
    const sorted = [...route.nodes].sort((a, b) => a.order - b.order);
    const idx = sorted.findIndex(
      (n) =>
        n.poi_id === deepPoi ||
        poisById[n.poi_id]?.poi_name === deepName ||
        poisById[n.poi_id]?.poi_name === deepPoi,
    );
    if (idx < 0) return null;
    if (idx >= sorted.length - 1) return { name: "", poiId: "" };
    const next = sorted[idx + 1];
    return {
      name: poisById[next.poi_id]?.poi_name ?? next.poi_id,
      poiId: next.poi_id,
    };
  }, [session, deepPoi, deepName]);

  const resolvedNextName =
    nextStopParam !== null ? nextStopParam : fromWalk ? (sessionNext?.name ?? null) : null;
  const resolvedNextId =
    nextStopId || (fromWalk ? (sessionNext?.poiId ?? "") : "");

  const [query, setQuery] = useState("");
  const [pois, setPois] = useState<POI[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [listReloadKey, setListReloadKey] = useState(0);
  const [selected, setSelected] = useState<POI | null>(null);
  const [generating, setGenerating] = useState(false);
  const [narration, setNarration] = useState<GuideGenerateResponse | null>(null);
  const [genError, setGenError] = useState<string | null>(null);

  const [chat, setChat] = useState<ChatTurn[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [askProgressStep, setAskProgressStep] = useState(0);

  const [resolvedScene, setResolvedScene] = useState<{ key: string; url: string }>({
    key: "",
    url: heroImg,
  });
  const [failedCuratedSceneKey, setFailedCuratedSceneKey] = useState("");
  const [sceneLoading, setSceneLoading] = useState(false);
  const deepLoaded = useRef<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoadingList(true);
    setListError(null);
    listPois({ limit: 500 }, { signal: controller.signal })
      .then((rows) => {
        if (controller.signal.aborted) return;
        setPois(Array.isArray(rows) ? rows : []);
        setListError(null);
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        const message = err instanceof Error ? err.message : "";
        setListError(
          message.includes("Failed to fetch") || message.includes("NetworkError")
            ? t(language, "backendDown")
            : t(language, "guideSearchError"),
        );
        setPois([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingList(false);
      });
    return () => {
      controller.abort();
    };
    // language only affects error copy; reload via listReloadKey / mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listReloadKey]);

  useEffect(() => {
    if (!asking) {
      setAskProgressStep(0);
      return;
    }
    const timer = window.setInterval(() => {
      setAskProgressStep((step) => Math.min(step + 1, 3));
    }, 1400);
    return () => window.clearInterval(timer);
  }, [asking]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return pois.slice(0, 24);
    return pois
      .filter((p) => {
        const hay = localizedPoiSearchText(p, language).toLowerCase();
        return hay.includes(q);
      })
      .slice(0, 40);
  }, [pois, query, language]);

  async function loadNarration(poi: POI, displayName?: string) {
    setSelected(poi);
    setGenerating(true);
    setGenError(null);
    setNarration(null);
    setChat([]);
    try {
      const gen = await generateGuide({
        poi: displayName || poi.poi_name,
        language,
        interests: preference?.interests,
        travel_type: preference?.travel_type,
        next_stop: resolvedNextName,
      });
      if (!gen.text && !gen.audio_script && !gen.immersive) {
        setGenError(gen.error || t(language, "guideError"));
        return;
      }
      setNarration(gen);
    } catch (err) {
      setGenError(err instanceof Error ? err.message : t(language, "guideError"));
    } finally {
      setGenerating(false);
    }
  }

  useEffect(() => {
    if (loadingList || !deepPoi) return;
    const key = `${deepPoi}|${deepName}|${resolvedNextName ?? "∅"}`;
    if (deepLoaded.current === key) return;
    const match =
      pois.find((p) => p.poi_id === deepPoi) ||
      pois.find((p) => p.poi_name === deepPoi || p.poi_name === deepName) ||
      pois.find(
        (p) =>
          p.poi_name.includes(deepName || deepPoi) ||
          (deepName || deepPoi).includes(p.poi_name),
      );
    if (match) {
      deepLoaded.current = key;
      void loadNarration(match, deepName || match.poi_name);
      return;
    }
    if (pois.length === 0) return;
    // 列表里没有精确匹配时，仍用名称拉讲解
    deepLoaded.current = key;
    const synthetic: POI = {
      poi_id: deepPoi,
      poi_name: deepName || deepPoi,
      alias: null,
      address: "",
      longitude: 0,
      latitude: 0,
      category: "",
      source: "deep-link",
      created_at: "",
      updated_at: "",
    };
    void loadNarration(synthetic, deepName || deepPoi);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- deep-link once per param set
  }, [loadingList, pois, deepPoi, deepName]);

  function selectPoi(poi: POI) {
    deepLoaded.current = poi.poi_id;
    setSearchParams({ poi: poi.poi_id, name: poi.poi_name });
    void loadNarration(poi);
  }

  async function submitQuestion(suggestedQuestion?: string) {
    const q = suggestedQuestion?.trim() || question.trim();
    const poiKey = selected?.poi_id || deepPoi || title || selected?.poi_name || deepName;
    if (!q || !poiKey || asking) return;
    setAskProgressStep(0);
    setAsking(true);
    setChat((prev) => [...prev, { role: "user", text: q }]);
    setQuestion("");
    try {
      const res = await askGuide({
        poi: poiKey,
        question: q,
        language,
        interests: preference?.interests,
      });
      setChat((prev) => [
        ...prev,
        {
          role: "assistant",
          text: res.text || t(language, "guideAskEmpty"),
          webUsed: Boolean(res.web_used),
          webSources: res.web_sources,
        },
      ]);
    } catch (err) {
      setChat((prev) => [
        ...prev,
        {
          role: "assistant",
          text: err instanceof Error ? err.message : t(language, "guideAskError"),
        },
      ]);
    } finally {
      setAsking(false);
    }
  }

  function onPhotoRecognized(name: string) {
    const match = pois.find(
      (p) => p.poi_name === name || p.poi_name.includes(name) || name.includes(p.poi_name),
    );
    if (match) {
      selectPoi(match);
      return;
    }
    // 本地列表只取前 40 条；没命中时仍用识别到的名称拉讲解
    selectPoi({
      poi_id: name,
      poi_name: name,
      alias: null,
      address: "",
      longitude: 0,
      latitude: 0,
      category: "",
      source: "photo",
      created_at: "",
      updated_at: "",
    });
  }

  const sceneName = selected?.poi_name || deepName || narration?.poi_name || "";
  const scenePoiId = selected?.poi_id || deepPoi || narration?.poi_id || "";
  const sceneKey = `${scenePoiId}|${sceneName}`;
  const curatedSceneUrl = curatedPoiImage(scenePoiId, sceneName);
  const sceneUrl =
    curatedSceneUrl && failedCuratedSceneKey !== sceneKey
      ? curatedSceneUrl
      : resolvedScene.key === sceneKey
        ? resolvedScene.url
        : heroImg;

  useEffect(() => {
    const name = sceneName;
    const poiId = scenePoiId;
    if (!name && !poiId) {
      setResolvedScene({ key: "", url: heroImg });
      setSceneLoading(false);
      return;
    }
    if (curatedPoiImage(poiId, name)) {
      setSceneLoading(false);
      return;
    }
    let cancelled = false;
    setSceneLoading(true);
    void resolvePoiImage({
      poiId,
      name,
      alias: selected?.alias,
      latitude: selected?.latitude,
      longitude: selected?.longitude,
    }).then((url) => {
      if (!cancelled) {
        setResolvedScene({ key: sceneKey, url });
        setSceneLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [
    selected?.alias,
    selected?.latitude,
    selected?.longitude,
    sceneKey,
    sceneName,
    scenePoiId,
  ]);

  function clearGuideSelection() {
    setSelected(null);
    setNarration(null);
    setChat([]);
    setSearchParams({});
    deepLoaded.current = null;
  }

  const deepLinkName = deepPoi
    ? localizedPoiName(
        { poi_id: deepPoi, poi_name: deepName || deepPoi, alias: null },
        language,
      )
    : "";
  const title = selected
    ? localizedPoiName(selected, language)
    : deepLinkName || narration?.poi_name || t(language, "guidePageTitle");
  const formatPlace = (key: Parameters<typeof t>[1]) =>
    t(language, key).split("{place}").join(title);
  const guideQuestionSuggestions = [
    formatPlace("guideAskSuggestionHistory"),
    formatPlace("guideAskSuggestionDetails"),
    formatPlace("guideAskSuggestionView"),
  ];
  const guideAskProgressSteps = [
    t(language, "guideAskProgressUnderstand"),
    t(language, "guideAskProgressWeb"),
    t(language, "guideAskProgressLocal"),
    t(language, "guideAskProgressCompose"),
  ];
  const showingDetail = Boolean(selected || deepPoi);
  const narrationSections = useMemo(() => {
    const script =
      narration?.audio_script ||
      narration?.immersive?.audio_script ||
      narration?.text ||
      "";
    if (!script && !narration?.immersive) return [];
    if (narration?.sections?.length) return narration.sections;
    return script ? sectionsFromText(script) : [];
  }, [narration]);
  const narrationImage =
    (sceneUrl && sceneUrl !== heroImg ? sceneUrl : null) ||
    curatedPoiImage(
      selected?.poi_id || deepPoi || narration?.poi_id,
      selected?.poi_name || deepName || narration?.poi_name,
    );

  return (
    <main className="flex-1 bg-paper pb-20">
      <div className="mx-auto max-w-5xl px-5 pt-6 lg:px-6">
        {showingDetail ? (
          <div className="mb-4">
            {fromWalk ? (
              <Link
                to="/walk"
                className="inline-flex items-center gap-1 text-sm text-ink-soft transition hover:text-ink"
              >
                {t(language, "guideBackToWalk")}
              </Link>
            ) : (
              <button
                type="button"
                onClick={clearGuideSelection}
                className="inline-flex items-center gap-1 text-sm text-ink-soft transition hover:text-ink"
              >
                {t(language, "guideBackToList")}
              </button>
            )}
          </div>
        ) : null}

        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
              {fromWalk ? t(language, "guideFromWalk") : t(language, "guidePageEyebrow")}
            </p>
            <h1 className="font-display text-3xl leading-tight text-ink lg:text-4xl">
              {showingDetail ? title : t(language, "guidePageTitle")}
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-soft">
              {t(language, "guideExperienceLead")}
            </p>
          </div>
        </div>

        <AzulejoBand className="mb-6" />

        {!selected && !deepPoi ? (
          <div className="mb-8">
            <label className="mb-4 block">
              <span className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.22em] text-ink-soft">
                {t(language, "guideSearchLabel")}
              </span>
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t(language, "guideSearchPlaceholder")}
                className="w-full rounded-2xl border border-line bg-card px-4 py-3.5 text-sm text-ink outline-none transition placeholder:text-ink-soft/60 focus:border-sage focus:ring-2 focus:ring-sage/30"
              />
            </label>
            {listError ? (
              <div className="mb-4 rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm">
                <p>{listError}</p>
                <button
                  type="button"
                  onClick={() => setListReloadKey((n) => n + 1)}
                  className="mt-3 text-sm font-medium text-sage-deep underline-offset-2 hover:underline"
                >
                  {t(language, "retry")}
                </button>
              </div>
            ) : null}
            {loadingList ? (
              <p className="text-sm text-ink-soft">{t(language, "guideSearching")}</p>
            ) : filtered.length === 0 ? (
              <p className="text-sm text-ink-soft">{t(language, "guideNoResults")}</p>
            ) : (
              <ul className="grid gap-2 sm:grid-cols-2">
                {filtered.map((poi) => (
                  <li key={poi.poi_id}>
                    <button
                      type="button"
                      onClick={() => selectPoi(poi)}
                      className="w-full rounded-2xl border border-line bg-card px-4 py-3 text-left transition hover:border-sage hover:bg-paper-warm"
                    >
                      <p className="font-serif text-[15px] text-ink">
                        {localizedPoiName(poi, language)}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-ink-soft">
                        {localizedPoiMeta(poi, language)}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}

        {selected || deepPoi ? (
          <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
            <section className="space-y-5">
              <div className="overflow-hidden rounded-[1.75rem] border border-sage-deep/20 bg-moss shadow-[var(--shadow-soft)]">
                <div className="relative aspect-[4/3] overflow-hidden bg-moss">
                  <img
                    src={sceneUrl}
                    alt={title}
                    className={`h-full w-full object-cover transition duration-500 ${
                      sceneLoading ? "opacity-60 scale-105" : "opacity-95"
                    }`}
                    onError={() => {
                      if (curatedSceneUrl) setFailedCuratedSceneKey(sceneKey);
                      setResolvedScene({ key: sceneKey, url: heroImg });
                      setSceneLoading(false);
                    }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-moss/90 via-moss/20 to-transparent" />
                  <div className="absolute inset-x-0 bottom-0 p-5 text-paper">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.2em] opacity-80">
                      {t(language, "guideVisualLabel")}
                    </p>
                    <h2 className="mt-1 font-display text-2xl">{title}</h2>
                    {selected ? (
                      <p className="mt-1 text-xs opacity-80">
                        {localizedPoiMeta(selected, language)}
                      </p>
                    ) : null}
                  </div>
                </div>
              </div>

              <PhotoRecognitionPanel
                language={language}
                tripId={trip?.trip_id ?? getLastTripId()}
                poiId={selected?.poi_id ?? deepPoi}
                token={token}
                onRecognized={onPhotoRecognized}
                onManualSelect={clearGuideSelection}
              />

              <div className="rounded-[1.75rem] border border-line bg-card/90 p-5 shadow-[var(--shadow-soft)] sm:p-6">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-sage-deep">
                  {t(language, "narrationTitle")}
                </p>
                {generating ? (
                  <p className="mt-3 text-sm text-ink-soft">{t(language, "generatingGuide")}</p>
                ) : null}
                {genError ? <p className="mt-3 text-sm text-clay">{genError}</p> : null}
                {narration?.text ||
                narration?.audio_script ||
                narration?.immersive ? (
                  <>
                    <GuideNarrationSections
                      key={`${title}-${narrationImage ?? "band"}`}
                      language={language}
                      sections={narrationSections}
                      immersive={narration?.immersive}
                      imageUrl={narrationImage}
                      imageAlt={title}
                      showImage
                    />
                    <LocalSpeechPlayer
                      text={
                        narration.audio_script ||
                        narration.immersive?.audio_script ||
                        narration.text ||
                        ""
                      }
                      language={language}
                    />
                    {resolvedNextName ? (
                      <Link
                        to={`/guide?${new URLSearchParams({
                          poi: resolvedNextId || resolvedNextName,
                          name: resolvedNextName,
                          from: "walk",
                        }).toString()}`}
                        className="mt-4 flex w-full items-center justify-between rounded-2xl border border-sage-deep/30 bg-sage-deep/8 px-4 py-3 text-sm text-ink transition hover:bg-sage-deep/12"
                        onClick={() => {
                          deepLoaded.current = null;
                        }}
                      >
                        <span>
                          <span className="block text-[10px] font-semibold uppercase tracking-[0.18em] text-sage-deep">
                            {t(language, "guideNextStopLabel")}
                          </span>
                          <span className="font-serif text-base">
                            {resolvedNextId && session?.poisById[resolvedNextId]
                              ? localizedPoiName(session.poisById[resolvedNextId], language)
                              : resolvedNextName}
                          </span>
                        </span>
                        <span aria-hidden className="text-sage-deep">
                          →
                        </span>
                      </Link>
                    ) : fromWalk && resolvedNextName === "" ? (
                      <p className="mt-4 text-xs text-ink-soft">{t(language, "guideLastStopNote")}</p>
                    ) : null}
                  </>
                ) : null}
                <button
                  type="button"
                  onClick={clearGuideSelection}
                  className="mt-4 text-sm text-sage-deep underline-offset-2 hover:underline"
                >
                  {t(language, "guidePickAnother")}
                </button>
              </div>
            </section>

            <section className="flex min-h-[28rem] flex-col overflow-hidden rounded-[1.75rem] border border-line bg-card shadow-[var(--shadow-soft)]">
              <div className="border-b border-line/80 bg-sage-deep/[0.06] px-5 py-5">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-sage-deep">
                  {t(language, "guideAskTitle")}
                </p>
                <h2 className="mt-1 font-serif text-lg leading-snug text-ink">
                  {formatPlace("guideAskLead")}
                </h2>
              </div>
              <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-5 py-5">
                {chat.length === 0 ? (
                  <div className="py-1">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-ink-soft">
                      {t(language, "guideAskSuggestionLabel")}
                    </p>
                    <div className="mt-3 grid gap-2">
                      {guideQuestionSuggestions.map((suggestion) => (
                        <button
                          key={suggestion}
                          type="button"
                          disabled={asking}
                          onClick={() => void submitQuestion(suggestion)}
                          className="group flex min-h-12 w-full items-center justify-between gap-3 rounded-xl border border-line bg-paper-warm/55 px-4 py-3 text-left text-sm leading-relaxed text-ink transition hover:border-sage hover:bg-paper-warm disabled:opacity-50"
                        >
                          <span>{suggestion}</span>
                          <span
                            aria-hidden
                            className="shrink-0 text-sage-deep transition group-hover:translate-x-0.5"
                          >
                            →
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  chat.map((turn, i) => (
                    <div
                      key={`${turn.role}-${i}`}
                      className={[
                        "w-fit max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
                        turn.role === "user"
                          ? "ml-auto bg-sage-deep text-paper"
                          : "mr-auto bg-paper-warm text-ink",
                      ].join(" ")}
                    >
                      <p className="whitespace-pre-wrap">{turn.text}</p>
                      {turn.role === "assistant" && turn.webUsed ? (
                        <p className="mt-2 text-[10px] uppercase tracking-[0.16em] text-sage-deep">
                          {t(language, "guideAskWebBadge")}
                        </p>
                      ) : null}
                    </div>
                  ))
                )}
                {asking ? (
                  <div
                    role="status"
                    aria-live="polite"
                    className="rounded-xl border border-line bg-paper-warm/65 px-4 py-3.5"
                  >
                    <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-sage-deep">
                      {t(language, "guideAskProgressLabel")}
                    </p>
                    <ol className="mt-3 grid gap-2 sm:grid-cols-2">
                      {guideAskProgressSteps.map((step, index) => {
                        const complete = index < askProgressStep;
                        const active = index === askProgressStep;
                        return (
                          <li
                            key={step}
                            className={`flex min-h-7 items-center gap-2 text-xs leading-snug ${
                              active || complete ? "text-ink" : "text-ink-soft/55"
                            }`}
                          >
                            <span
                              aria-hidden
                              className={`flex size-4 shrink-0 items-center justify-center rounded-full border ${
                                complete
                                  ? "border-sage-deep bg-sage-deep text-paper"
                                  : active
                                    ? "border-sage-deep bg-card"
                                    : "border-line bg-transparent"
                              }`}
                            >
                              {complete ? (
                                <span className="text-[9px] leading-none">✓</span>
                              ) : active ? (
                                <span className="size-1.5 animate-pulse rounded-full bg-sage-deep" />
                              ) : null}
                            </span>
                            <span>{step}</span>
                          </li>
                        );
                      })}
                    </ol>
                  </div>
                ) : null}
              </div>
              <form
                className="flex gap-2 border-t border-line bg-paper-warm/50 p-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  void submitQuestion();
                }}
              >
                <input
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder={t(language, "guideAskPlaceholder")}
                  className="min-w-0 flex-1 rounded-full border border-line bg-card px-4 py-2.5 text-sm outline-none focus:border-sage"
                />
                <button
                  type="submit"
                  disabled={asking || !question.trim()}
                  className="shrink-0 rounded-full bg-sage-deep px-4 py-2.5 text-sm font-medium text-paper disabled:opacity-50"
                >
                  {t(language, "guideAskSend")}
                </button>
              </form>
            </section>
          </div>
        ) : null}
      </div>
    </main>
  );
}
