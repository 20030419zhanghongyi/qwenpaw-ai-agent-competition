import { useEffect, useState } from "react";
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
  },
  "zh-TW": {
    history: "歷史行程與收藏", empty: "暫時沒有儲存的行程或收藏。", favorite: "收藏地點",
    remove: "移除收藏", completed: "已完成", active: "進行中", feedback: "提交本次回饋",
    feedbackHint: "評分和回饋會用於改善路線，不會儲存精確位置。", send: "提交回饋", sent: "已儲存回饋",
  },
  en: {
    history: "Trip history and saved places", empty: "No saved trips or places yet.", favorite: "Saved places",
    remove: "Remove", completed: "Completed", active: "Active", feedback: "Rate this trip",
    feedbackHint: "Feedback improves routes; precise location is never saved.", send: "Save feedback", sent: "Feedback saved",
  },
  pt: {
    history: "Histórico e locais guardados", empty: "Ainda não há viagens ou locais guardados.", favorite: "Locais guardados",
    remove: "Remover", completed: "Concluída", active: "Em curso", feedback: "Avaliar esta viagem",
    feedbackHint: "O feedback melhora os percursos; a localização exata não é guardada.", send: "Guardar feedback", sent: "Feedback guardado",
  },
} as const;

export function TravelHistoryPanel({ userId, language }: { userId: string | null; language: LanguageCode }) {
  const copy = COPY[language];
  const [history, setHistory] = useState<HistoryTrip[]>([]);
  const [favorites, setFavorites] = useState<FavoritePoi[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [feedbackTrip, setFeedbackTrip] = useState<string | null>(null);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [sent, setSent] = useState(false);

  useEffect(() => {
    if (!userId) return;
    void Promise.all([listTripHistory(userId), listFavoritePois(userId)])
      .then(([trips, saved]) => { setHistory(trips); setFavorites(saved); })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Unable to load profile"));
  }, [userId]);

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

  return <section className="mb-8 rounded-2xl border border-line bg-card px-5 py-5 shadow-[var(--shadow-soft)]">
    <h2 className="font-display text-xl text-ink">{copy.history}</h2>
    {error ? <p className="mt-3 text-sm text-clay">{error}</p> : null}
    {!error && history.length === 0 && favorites.length === 0 ? <p className="mt-3 text-sm text-ink-soft">{copy.empty}</p> : null}
    {history.length > 0 ? <div className="mt-4 space-y-3">
      {history.map((trip) => <div key={trip.trip_id} className="rounded-xl border border-line/70 px-4 py-3">
        <div className="flex items-center justify-between gap-3 text-sm text-ink"><span>{trip.route_id}</span><span className="text-ink-soft">{trip.status === "completed" ? copy.completed : copy.active}</span></div>
        <p className="mt-1 text-xs text-ink-soft">{trip.completed_stops}/{trip.total_stops} stops · {Math.round(trip.completion_ratio * 100)}%</p>
        {trip.status === "completed" ? <button type="button" onClick={() => { setFeedbackTrip(trip.trip_id); setSent(false); }} className="mt-3 text-xs font-medium text-sage-deep">{copy.feedback}</button> : null}
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
