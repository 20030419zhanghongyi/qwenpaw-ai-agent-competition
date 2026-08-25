import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createMemoir,
  getTripMemoir,
  type MemoirStyle,
  type TravelMemoir,
} from "@/api/memoirs";
import {
  listFavoritePois,
  listTripHistory,
  removeFavoritePoi,
  submitTripFeedback,
  type FavoritePoi,
  type HistoryTrip,
} from "@/api/profile";
import type { LanguageCode } from "@/types";

const COPY = {
  "zh-CN": {
    history: "历史行程与收藏", empty: "暂时没有保存的行程或收藏。", favorite: "收藏地点",
    remove: "移除收藏", completed: "已完成", active: "进行中", feedback: "提交本次反馈",
    feedbackHint: "评分和反馈会用于改进路线，不会保存精确位置。", send: "提交反馈", sent: "已保存反馈",
    memoir: "旅行回忆录", createMemoir: "创建回忆录", editMemoir: "继续编辑", viewMemoir: "查看回忆录",
    chooseStyle: "选择叙事风格", diary: "温柔日记", magazine: "旅行杂志", social: "轻松短句", documentary: "纪录片旁白",
    needCheckin: "至少完成一次打卡后即可创建。", creating: "正在创建…",
  },
  "zh-TW": {
    history: "歷史行程與收藏", empty: "暫時沒有儲存的行程或收藏。", favorite: "收藏地點",
    remove: "移除收藏", completed: "已完成", active: "進行中", feedback: "提交本次回饋",
    feedbackHint: "評分和回饋會用於改善路線，不會儲存精確位置。", send: "提交回饋", sent: "已儲存回饋",
    memoir: "旅行回憶錄", createMemoir: "建立回憶錄", editMemoir: "繼續編輯", viewMemoir: "查看回憶錄",
    chooseStyle: "選擇敘事風格", diary: "溫柔日記", magazine: "旅行雜誌", social: "輕鬆短句", documentary: "紀錄片旁白",
    needCheckin: "至少完成一次打卡後即可建立。", creating: "正在建立…",
  },
  en: {
    history: "Trip history and saved places", empty: "No saved trips or places yet.", favorite: "Saved places",
    remove: "Remove", completed: "Completed", active: "Active", feedback: "Rate this trip",
    feedbackHint: "Feedback improves routes; precise location is never saved.", send: "Save feedback", sent: "Feedback saved",
    memoir: "Travel memoir", createMemoir: "Create memoir", editMemoir: "Continue editing", viewMemoir: "View memoir",
    chooseStyle: "Choose a narrative style", diary: "Gentle diary", magazine: "Travel magazine", social: "Short and light", documentary: "Documentary",
    needCheckin: "Create one after at least one check-in.", creating: "Creating…",
  },
  pt: {
    history: "Histórico e locais guardados", empty: "Ainda não há viagens ou locais guardados.", favorite: "Locais guardados",
    remove: "Remover", completed: "Concluída", active: "Em curso", feedback: "Avaliar esta viagem",
    feedbackHint: "O feedback melhora os percursos; a localização exata não é guardada.", send: "Guardar feedback", sent: "Feedback guardado",
    memoir: "Memórias de viagem", createMemoir: "Criar memórias", editMemoir: "Continuar a editar", viewMemoir: "Ver memórias",
    chooseStyle: "Escolher estilo narrativo", diary: "Diário suave", magazine: "Revista de viagem", social: "Frases leves", documentary: "Documentário",
    needCheckin: "Disponível após pelo menos um check-in.", creating: "A criar…",
  },
} as const;

export function TravelHistoryPanel({ userId, token, language }: { userId: string | null; token: string | null; language: LanguageCode }) {
  const navigate = useNavigate();
  const copy = COPY[language];
  const [history, setHistory] = useState<HistoryTrip[]>([]);
  const [favorites, setFavorites] = useState<FavoritePoi[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [feedbackTrip, setFeedbackTrip] = useState<string | null>(null);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [sent, setSent] = useState(false);
  const [memoirs, setMemoirs] = useState<Record<string, TravelMemoir>>({});
  const [styleTrip, setStyleTrip] = useState<string | null>(null);
  const [creatingTrip, setCreatingTrip] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;
    void Promise.all([listTripHistory(userId), listFavoritePois(userId)])
      .then(async ([trips, saved]) => {
        setHistory(trips); setFavorites(saved);
        if (!token) return;
        const found = await Promise.all(trips.map(async (trip) => {
          try { return await getTripMemoir(trip.trip_id, token); } catch { return null; }
        }));
        setMemoirs(Object.fromEntries(found.filter(Boolean).map((memoir) => [memoir!.trip_id, memoir!])));
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Unable to load profile"));
  }, [userId, token]);

  if (!userId) return null;
  const remove = async (poiId: string) => {
    await removeFavoritePoi(userId, poiId);
    setFavorites((items) => items.filter((item) => item.poi_id !== poiId));
  };
  const sendFeedback = async () => {
    if (!feedbackTrip) return;
    await submitTripFeedback({ tripId: feedbackTrip, userId, rating, comment });
    setSent(true);
  };
  const startMemoir = async (tripId: string, style: MemoirStyle) => {
    if (!token) return;
    setCreatingTrip(tripId);
    setError(null);
    try {
      const memoir = await createMemoir(tripId, style, language, token);
      setMemoirs((current) => ({ ...current, [tripId]: memoir }));
      navigate(`/profile/memoirs/${encodeURIComponent(memoir.memoir_id)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create memoir");
    } finally { setCreatingTrip(null); }
  };

  return <section className="mb-8 rounded-2xl border border-line bg-card px-5 py-5 shadow-[var(--shadow-soft)]">
    <h2 className="font-display text-xl text-ink">{copy.history}</h2>
    {error ? <p className="mt-3 text-sm text-clay">{error}</p> : null}
    {!error && history.length === 0 && favorites.length === 0 ? <p className="mt-3 text-sm text-ink-soft">{copy.empty}</p> : null}
    {history.length > 0 ? <div className="mt-4 space-y-3">
      {history.map((trip) => <div key={trip.trip_id} className="rounded-xl border border-line/70 px-4 py-3">
        <div className="flex items-center justify-between gap-3 text-sm text-ink"><span>{trip.route_id}</span><span className="text-ink-soft">{trip.status === "completed" ? copy.completed : copy.active}</span></div>
        <p className="mt-1 text-xs text-ink-soft">{trip.completed_stops}/{trip.total_stops} stops · {Math.round(trip.completion_ratio * 100)}%</p>
        <div className="mt-3 flex flex-wrap gap-4">
          {memoirs[trip.trip_id] ? <button type="button" onClick={() => navigate(`/profile/memoirs/${encodeURIComponent(memoirs[trip.trip_id].memoir_id)}`)} className="text-xs font-medium text-sage-deep">{memoirs[trip.trip_id].status === "completed" ? copy.viewMemoir : copy.editMemoir}</button> : trip.completed_stops > 0 ? <button type="button" onClick={() => setStyleTrip(styleTrip === trip.trip_id ? null : trip.trip_id)} className="text-xs font-medium text-sage-deep">{creatingTrip === trip.trip_id ? copy.creating : copy.createMemoir}</button> : <span className="text-xs text-ink-soft">{copy.needCheckin}</span>}
          {trip.status === "completed" ? <button type="button" onClick={() => { setFeedbackTrip(trip.trip_id); setSent(false); }} className="text-xs font-medium text-sage-deep">{copy.feedback}</button> : null}
        </div>
        {styleTrip === trip.trip_id && !memoirs[trip.trip_id] ? <div className="mt-3 rounded-xl bg-paper-warm p-3"><p className="text-xs text-ink-soft">{copy.chooseStyle}</p><div className="mt-2 flex flex-wrap gap-2">{([['diary', copy.diary], ['magazine', copy.magazine], ['social', copy.social], ['documentary', copy.documentary]] as Array<[MemoirStyle, string]>).map(([style, label]) => <button key={style} type="button" disabled={Boolean(creatingTrip)} onClick={() => void startMemoir(trip.trip_id, style)} className="rounded-full border border-sage-deep px-3 py-1.5 text-xs text-sage-deep disabled:opacity-50">{label}</button>)}</div></div> : null}
      </div>)}
    </div> : null}
    {favorites.length > 0 ? <div className="mt-5"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-sage-deep">{copy.favorite}</p>
      <ul className="mt-2 space-y-2">{favorites.map((item) => <li key={item.poi_id} className="flex justify-between gap-3 text-sm text-ink"><span>{item.poi_name}</span><button type="button" onClick={() => void remove(item.poi_id)} className="text-xs text-clay">{copy.remove}</button></li>)}</ul>
    </div> : null}
    {feedbackTrip ? <div className="mt-5 rounded-xl bg-paper-warm p-4"><p className="text-sm font-medium text-ink">{copy.feedback}</p><p className="mt-1 text-xs text-ink-soft">{copy.feedbackHint}</p>
      <select value={rating} onChange={(event) => setRating(Number(event.target.value))} className="mt-3 rounded-lg border border-line bg-card px-3 py-2 text-sm"><option value={5}>5 / 5</option><option value={4}>4 / 5</option><option value={3}>3 / 5</option><option value={2}>2 / 5</option><option value={1}>1 / 5</option></select>
      <textarea value={comment} onChange={(event) => setComment(event.target.value)} className="mt-3 w-full rounded-lg border border-line bg-card p-3 text-sm" rows={2} />
      <button type="button" onClick={() => void sendFeedback()} className="mt-3 rounded-full bg-sage-deep px-4 py-2 text-sm text-paper">{copy.send}</button>{sent ? <span className="ml-3 text-xs text-sage-deep">{copy.sent}</span> : null}
    </div> : null}
  </section>;
}
