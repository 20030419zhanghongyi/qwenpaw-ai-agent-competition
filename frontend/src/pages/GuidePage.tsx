import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  askGuide,
  generateGuide,
  listPois,
  recognizeGuidePhoto,
  synthesizeTts,
  type GuideGenerateResponse,
} from "@/api/client";
import heroImg from "@/assets/hero-ruins.jpg";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { t } from "@/i18n";
import { resolvePoiImage } from "@/lib/poiImage";
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
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [ttsFailed, setTtsFailed] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  const [chat, setChat] = useState<ChatTurn[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);

  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoBusy, setPhotoBusy] = useState(false);
  const [photoNote, setPhotoNote] = useState<string | null>(null);
  const [sceneUrl, setSceneUrl] = useState<string>(heroImg);
  const [sceneLoading, setSceneLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
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

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return pois.slice(0, 24);
    return pois
      .filter((p) => {
        const hay = `${p.poi_name} ${p.alias ?? ""} ${p.address} ${p.category}`.toLowerCase();
        return hay.includes(q);
      })
      .slice(0, 40);
  }, [pois, query]);

  async function loadNarration(poi: POI, displayName?: string) {
    setSelected(poi);
    setGenerating(true);
    setGenError(null);
    setNarration(null);
    setAudioUrl(null);
    setTtsFailed(false);
    setChat([]);
    setPhotoNote(null);
    try {
      const gen = await generateGuide({
        poi: displayName || poi.poi_name,
        language,
        interests: preference?.interests,
        next_stop: resolvedNextName,
      });
      if (!gen.text) {
        setGenError(gen.error || t(language, "guideError"));
        return;
      }
      setNarration(gen);
      void (async () => {
        try {
          const tts = await synthesizeTts({ text: gen.text, language });
          setAudioUrl(tts.audio_url);
        } catch {
          setTtsFailed(true);
        }
      })();
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

  async function submitQuestion() {
    const q = question.trim();
    const poiKey = selected?.poi_name || deepName || deepPoi;
    if (!q || !poiKey || asking) return;
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

  async function onPhotoPicked(file: File | null) {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPhotoPreview(url);
    setPhotoBusy(true);
    setPhotoNote(null);
    try {
      const res = await recognizeGuidePhoto({ file, language });
      if (res.candidate_poi) {
        setPhotoNote(
          `${t(language, "guidePhotoRecognized")}${res.candidate_poi}${
            res.confidence != null ? ` · ${Math.round(res.confidence * 100)}%` : ""
          }`,
        );
        const match = pois.find(
          (p) =>
            p.poi_name === res.candidate_poi ||
            p.poi_name.includes(res.candidate_poi!) ||
            res.candidate_poi!.includes(p.poi_name),
        );
        if (match) {
          selectPoi(match);
        } else if (res.explanation?.text) {
          setNarration({
            text: res.explanation.text,
            poi_name: res.candidate_poi,
            source: "photo",
            source_type: res.explanation.source_type,
          });
          setSelected((prev) =>
            prev ?? {
              poi_id: res.candidate_poi || "photo",
              poi_name: res.candidate_poi || t(language, "guidePhotoUnknown"),
              alias: null,
              address: "",
              longitude: 0,
              latitude: 0,
              category: "",
              source: "photo",
              created_at: "",
              updated_at: "",
            },
          );
        }
      } else {
        setPhotoNote(res.low_confidence_hint || res.error || t(language, "guidePhotoUncertain"));
        if (res.description) {
          setChat((prev) => [
            ...prev,
            {
              role: "assistant",
              text: `${t(language, "guidePhotoSeen")}${res.description}`,
            },
          ]);
        }
      }
    } catch (err) {
      setPhotoNote(err instanceof Error ? err.message : t(language, "guidePhotoError"));
    } finally {
      setPhotoBusy(false);
    }
  }

  useEffect(() => {
    if (photoPreview) {
      setSceneUrl(photoPreview);
      return;
    }
    const name = selected?.poi_name || deepName || narration?.poi_name || "";
    const poiId = selected?.poi_id || deepPoi || "";
    if (!name && !poiId) {
      setSceneUrl(heroImg);
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
        setSceneUrl(url);
        setSceneLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [
    photoPreview,
    selected?.poi_id,
    selected?.poi_name,
    selected?.alias,
    selected?.latitude,
    selected?.longitude,
    deepPoi,
    deepName,
    narration?.poi_name,
  ]);

  function clearGuideSelection() {
    setSelected(null);
    setNarration(null);
    setAudioUrl(null);
    setChat([]);
    setPhotoPreview(null);
    setPhotoNote(null);
    setSearchParams({});
    deepLoaded.current = null;
  }

  const title =
    narration?.poi_name || selected?.poi_name || deepName || t(language, "guidePageTitle");
  const showingDetail = Boolean(selected || deepPoi);

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
                      <p className="font-serif text-[15px] text-ink">{poi.poi_name}</p>
                      <p className="mt-0.5 truncate text-xs text-ink-soft">
                        {[poi.category, poi.address].filter(Boolean).join(" · ")}
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
                      sceneLoading && !photoPreview ? "opacity-60 scale-105" : "opacity-95"
                    }`}
                    onError={() => setSceneUrl(heroImg)}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-moss/90 via-moss/20 to-transparent" />
                  <div className="absolute inset-x-0 bottom-0 p-5 text-paper">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.2em] opacity-80">
                      {photoPreview
                        ? t(language, "guidePhotoYourShot")
                        : t(language, "guideVisualLabel")}
                    </p>
                    <h2 className="mt-1 font-display text-2xl">{title}</h2>
                    {selected?.address ? (
                      <p className="mt-1 text-xs opacity-80">{selected.address}</p>
                    ) : null}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-3 border-t border-paper/10 bg-moss/95 px-5 py-4">
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    capture="environment"
                    className="hidden"
                    onChange={(e) => void onPhotoPicked(e.target.files?.[0] ?? null)}
                  />
                  <button
                    type="button"
                    disabled={photoBusy}
                    onClick={() => fileRef.current?.click()}
                    className="rounded-full bg-paper px-5 py-2.5 text-sm font-medium text-moss transition hover:bg-paper-warm disabled:opacity-60"
                  >
                    {photoBusy ? t(language, "guidePhotoUploading") : t(language, "guidePhotoUpload")}
                  </button>
                  <p className="text-xs text-paper/75">{t(language, "guidePhotoHint")}</p>
                </div>
                {photoNote ? (
                  <p className="border-t border-paper/10 px-5 py-3 text-xs text-paper/85">
                    {photoNote}
                  </p>
                ) : null}
              </div>

              <div className="rounded-[1.75rem] border border-line bg-card/90 p-5 shadow-[var(--shadow-soft)] sm:p-6">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-sage-deep">
                  {t(language, "narrationTitle")}
                </p>
                {generating ? (
                  <p className="mt-3 text-sm text-ink-soft">{t(language, "generatingGuide")}</p>
                ) : null}
                {genError ? <p className="mt-3 text-sm text-clay">{genError}</p> : null}
                {narration?.text ? (
                  <>
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-ink">
                      {narration.text}
                    </p>
                    {audioUrl ? (
                      <audio controls src={audioUrl} className="mt-4 w-full" />
                    ) : ttsFailed ? (
                      <p className="mt-3 text-xs text-ink-soft">{t(language, "ttsUnavailable")}</p>
                    ) : null}
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
                          <span className="font-serif text-base">{resolvedNextName}</span>
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
              <div className="border-b border-line/80 bg-sage-deep/[0.06] px-5 py-4">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-sage-deep">
                  {t(language, "guideAskTitle")}
                </p>
                <p className="mt-1 text-sm text-ink-soft">{t(language, "guideAskLead")}</p>
              </div>
              <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-5 py-4">
                {chat.length === 0 ? (
                  <p className="text-sm leading-relaxed text-ink-soft">
                    {t(language, "guideAskHint")}
                  </p>
                ) : (
                  chat.map((turn, i) => (
                    <div
                      key={`${turn.role}-${i}`}
                      className={[
                        "max-w-[92%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
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
                  <p className="text-xs text-ink-soft">{t(language, "guideAskThinking")}</p>
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
