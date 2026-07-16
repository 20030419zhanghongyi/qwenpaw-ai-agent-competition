import { useEffect, useMemo, useState } from "react";
import { LANG_OPTIONS, t, type Lang } from "./i18n";
import {
  getPois,
  getWalkPath,
  generateGuide,
  triggerGuide,
  matchRoutes,
  type GuideNarration,
  type GuideRequest,
  type MatchResult,
  type POI,
  type Preference,
  type WalkPath,
} from "./api/client";

type Step = "lang" | "pref" | "result";

const DURATIONS = ["half-day", "full-day", "evening"];
const INTERESTS = ["history", "architecture", "food", "photo", "culture", "relax"];
const TRAVEL_TYPES = ["solo", "friends", "family"];
const PHYSICAL = ["lessWalk", "noBacktrack"];

export default function App() {
  const [step, setStep] = useState<Step>("lang");
  const [lang, setLang] = useState<Lang>("zh-CN");
  const [duration, setDuration] = useState("half-day");
  const [interests, setInterests] = useState<string[]>(["photo", "architecture"]);
  const [travelType, setTravelType] = useState<string[]>(["solo"]);
  const [physical, setPhysical] = useState<string[]>(["lessWalk"]);

  const [loading, setLoading] = useState(false);
  const [matches, setMatches] = useState<MatchResult[] | null>(null);
  const [pois, setPois] = useState<POI[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pref: Preference = useMemo(
    () => ({
      duration,
      interests,
      travel_type: travelType,
      physical: physical.map((p) => (p === "lessWalk" ? "less-walk" : "no-backtrack")),
      language: lang,
    }),
    [duration, interests, travelType, physical, lang],
  );

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const [matchRes, poiList] = await Promise.all([matchRoutes(pref), getPois()]);
      setMatches(matchRes.matches);
      setPois(poiList);
      setStep("result");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const toggle = (list: string[], set: (v: string[]) => void, val: string) =>
    set(list.includes(val) ? list.filter((x) => x !== val) : [...list, val]);

  const tt = (k: string) => t(lang, k);

  return (
    <div className="app">
      <h1>{tt("appTitle")}</h1>
      <div className="steps">
        {step === "lang" ? "1/3" : step === "pref" ? "2/3" : "3/3"}
      </div>

      {error && <div className="card" style={{ color: "var(--primary)" }}>{tt("error")}: {error}</div>}

      {step === "lang" && (
        <div className="card">
          <h2>{tt("chooseLang")}</h2>
          <div className="row">
            {LANG_OPTIONS.map((o) => (
              <span
                key={o.code}
                className={`chip ${lang === o.code ? "on" : ""}`}
                onClick={() => setLang(o.code)}
              >
                {o.label}
              </span>
            ))}
          </div>
          <div style={{ height: 16 }} />
          <button className="primary" onClick={() => setStep("pref")}>{tt("start")}</button>
        </div>
      )}

      {step === "pref" && (
        <div className="card">
          <h2>{tt("preferences")}</h2>

          <p className="muted">{tt("duration")}</p>
          <div className="row">
            {DURATIONS.map((d) => (
              <span key={d} className={`chip ${duration === d ? "on" : ""}`} onClick={() => setDuration(d)}>
                {tt(d)}
              </span>
            ))}
          </div>

          <p className="muted">{tt("interests")}</p>
          <div className="row">
            {INTERESTS.map((i) => (
              <span key={i} className={`chip ${interests.includes(i) ? "on" : ""}`} onClick={() => toggle(interests, setInterests, i)}>
                {i}
              </span>
            ))}
          </div>

          <p className="muted">{tt("travelType")}</p>
          <div className="row">
            {TRAVEL_TYPES.map((i) => (
              <span key={i} className={`chip ${travelType.includes(i) ? "on" : ""}`} onClick={() => toggle(travelType, setTravelType, i)}>
                {i}
              </span>
            ))}
          </div>

          <p className="muted">{tt("physical")}</p>
          <div className="row">
            {PHYSICAL.map((i) => (
              <span key={i} className={`chip ${physical.includes(i) ? "on" : ""}`} onClick={() => toggle(physical, setPhysical, i)}>
                {tt(i)}
              </span>
            ))}
          </div>

          <div style={{ height: 16 }} />
          <button className="primary" disabled={loading} onClick={generate}>
            {loading ? tt("matching") : tt("generate")}
          </button>
        </div>
      )}

      {step === "result" && matches && pois && (
        <ResultView matches={matches} pois={pois} lang={lang} onBack={() => setStep("pref")} />
      )}
    </div>
  );
}

function ResultView({
  matches,
  pois,
  lang,
  onBack,
}: {
  matches: MatchResult[];
  pois: POI[];
  lang: Lang;
  onBack: () => void;
}) {
  const top = matches[0];
  const poiMap = useMemo(() => new Map(pois.map((p) => [p.poi_id, p])), [pois]);
  const tt = (k: string) => t(lang, k);
  const orderedNodes = top.route.nodes.slice().sort((a, b) => a.order - b.order);
  const [walkPath, setWalkPath] = useState<WalkPath | null>(null);
  const [guideRequest, setGuideRequest] = useState<GuideRequest | null>(null);
  const [narration, setNarration] = useState<GuideNarration | null>(null);
  const [guideError, setGuideError] = useState<string | null>(null);
  const [guideLoading, setGuideLoading] = useState(false);

  useEffect(() => {
    getWalkPath(orderedNodes.map((node) => node.poi_id)).then(setWalkPath).catch(() => setWalkPath(null));
  }, [top.route.id]);

  function checkLocation() {
    setGuideError(null);
    if (!navigator.geolocation) { setGuideError("此浏览器不支持定位，请从节点列表选择地点。"); return; }
    navigator.geolocation.getCurrentPosition(async ({ coords }) => {
      try {
        const sessionId = localStorage.getItem("storywalk-session") ?? crypto.randomUUID();
        localStorage.setItem("storywalk-session", sessionId);
        const result = await triggerGuide(coords.longitude, coords.latitude, sessionId, lang);
        if (result.triggered && result.guide_request) setGuideRequest(result.guide_request);
        else setGuideError(result.reason === "recently_triggered" ? "这个地点刚刚已提示过。" : "80 米内没有可讲解地点。");
      } catch (error) { setGuideError((error as Error).message); }
    }, () => setGuideError("无法取得当前位置，请允许浏览器定位权限。"));
  }

  async function confirmGuide(request: GuideRequest) {
    setGuideLoading(true); setGuideError(null);
    try { setNarration(await generateGuide(request)); setGuideRequest(null); }
    catch (error) { setGuideError((error as Error).message); }
    finally { setGuideLoading(false); }
  }

  return (
    <>
      <div className="card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2 style={{ margin: 0 }}>{tt("routeResult")}</h2>
          <button className="chip" onClick={onBack}>{tt("back")}</button>
        </div>
        <h2 style={{ marginTop: 12 }}>{top.route.name}</h2>
        <p className="muted">
          {top.route.duration_label} · 约 {top.route.duration_hours}h · {top.route.walk_distance_km}km ·
          体力 {top.route.physical_level}
        </p>
        <p>{top.route.description}</p>
        {walkPath && <p className="route-metrics">真实步行：{walkPath.total_walk_m} 米 · 约 {walkPath.total_walk_min} 分钟</p>}
        <button className="primary" onClick={checkLocation}>检查我是否靠近讲解点</button>
        <p className="muted">{tt("reasons")}</p>
        <div className="row">
          {top.reasons.map((r, i) => (
            <span key={i} className="chip on" style={{ background: "var(--accent)", color: "#5a4a00" }}>{r}</span>
          ))}
        </div>
      </div>

      <div className="card">
        <h2>{tt("nodes")}</h2>
        {orderedNodes
          .map((n) => {
            const poi = poiMap.get(n.poi_id);
            return (
              <div key={n.poi_id} className="node">
                <strong>{n.order}. {poi?.poi_name ?? n.poi_id}</strong>
                <div className="muted">建议停留 {n.suggested_stay_min} 分钟{poi ? ` · ${poi.address}` : ""}</div>
                {n.note && <div>{n.note}</div>}
                {poi && (
                  <div style={{ marginTop: 8 }}>
                    <div className="muted">{poi.category}</div>
                    <span className="muted">数据来源：{poi.source}</span>
                  </div>
                )}
              </div>
            );
          })}
      </div>
      {(guideRequest || narration || guideError) && <div className="card guide-panel">
        {guideRequest && <><h2>附近讲解</h2><p>已靠近 {guideRequest.poi}，要听讲解吗？</p><button className="primary" disabled={guideLoading} onClick={() => confirmGuide(guideRequest)}>{guideLoading ? "正在生成…" : "生成讲解"}</button></>}
        {narration?.text && <><h2>讲解</h2><p>{narration.text}</p><p className="muted">可信度：{Math.round(narration.confidence * 100)}%</p></>}
        {guideError && <p className="guide-error">{guideError}</p>}
      </div>}
    </>
  );
}
