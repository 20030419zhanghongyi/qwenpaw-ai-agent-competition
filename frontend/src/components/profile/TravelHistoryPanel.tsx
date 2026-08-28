import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createMemoir,
  getTripMemoir,
  type TravelMemoir,
} from "@/api/memoirs";
import {
  listFavoritePois,
  listTripHistory,
  removeFavoritePoi,
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
    needCheckin: "至少完成一次打卡后即可创建。", creating: "正在创建…", stops: "站",
  },
  "zh-TW": {
    history: "歷史行程與收藏", empty: "暫時沒有儲存的行程或收藏。", favorite: "收藏地點",
    remove: "移除收藏", completed: "已完成", active: "進行中", feedback: "提交本次回饋",
    feedbackHint: "評分和回饋會用於改善路線，不會儲存精確位置。", send: "提交回饋", sent: "已儲存回饋",
    memoir: "旅行回憶錄", createMemoir: "建立回憶錄", editMemoir: "繼續編輯", viewMemoir: "查看回憶錄",
    chooseStyle: "選擇敘事風格", diary: "溫柔日記", magazine: "旅行雜誌", social: "輕鬆短句", documentary: "紀錄片旁白",
    needCheckin: "至少完成一次打卡後即可建立。", creating: "正在建立…", stops: "站",
  },
  en: {
    history: "Trip history and saved places", empty: "No saved trips or places yet.", favorite: "Saved places",
    remove: "Remove", completed: "Completed", active: "Active", feedback: "Rate this trip",
    feedbackHint: "Feedback improves routes; precise location is never saved.", send: "Save feedback", sent: "Feedback saved",
    memoir: "Travel memoir", createMemoir: "Create memoir", editMemoir: "Continue editing", viewMemoir: "View memoir",
    chooseStyle: "Choose a narrative style", diary: "Gentle diary", magazine: "Travel magazine", social: "Short and light", documentary: "Documentary",
    needCheckin: "Create one after at least one check-in.", creating: "Creating…", stops: "stops",
  },
  pt: {
    history: "Histórico e locais guardados", empty: "Ainda não há viagens ou locais guardados.", favorite: "Locais guardados",
    remove: "Remover", completed: "Concluída", active: "Em curso", feedback: "Avaliar esta viagem",
    feedbackHint: "O feedback melhora os percursos; a localização exata não é guardada.", send: "Guardar feedback", sent: "Feedback guardado",
    memoir: "Memórias de viagem", createMemoir: "Criar memórias", editMemoir: "Continuar a editar", viewMemoir: "Ver memórias",
    chooseStyle: "Escolher estilo narrativo", diary: "Diário suave", magazine: "Revista de viagem", social: "Frases leves", documentary: "Documentário",
    needCheckin: "Disponível após pelo menos um check-in.", creating: "A criar…", stops: "paragens",
  },
} as const;

export function TravelHistoryPanel({ userId, token, language }: { userId: string | null; token: string | null; language: LanguageCode }) {
  const navigate = useNavigate();
  const copy = COPY[language];
  const [history, setHistory] = useState<HistoryTrip[]>([]);
  const [favorites, setFavorites] = useState<FavoritePoi[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [memoirs, setMemoirs] = useState<Record<string, TravelMemoir>>({});
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
  const startMemoir = async (tripId: string) => {
    if (!token) return;
    setCreatingTrip(tripId);
    setError(null);
    try {
      const memoir = await createMemoir(tripId, "magazine", language, token);
      setMemoirs((current) => ({ ...current, [tripId]: memoir }));
      navigate(`/profile/memoirs/${encodeURIComponent(memoir.memoir_id)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create memoir");
    } finally { setCreatingTrip(null); }
  };
  const tripDate = (value: string) =>
    new Intl.DateTimeFormat(language, {
      year: "numeric",
      month: "long",
      day: "numeric",
    }).format(new Date(value));

  return <section className="mb-8 rounded-2xl border border-line bg-card px-5 py-5 shadow-[var(--shadow-soft)]">
    <h2 className="font-display text-xl text-ink">{copy.history}</h2>
    {error ? <p className="mt-3 text-sm text-clay">{error}</p> : null}
    {!error && history.length === 0 && favorites.length === 0 ? <p className="mt-3 text-sm text-ink-soft">{copy.empty}</p> : null}
    {history.length > 0 ? <div className="mt-4 space-y-3">
      {history.map((trip) => <div key={trip.trip_id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 rounded-xl border border-line/70 px-4 py-4">
        <div className="min-w-0">
          <div className="text-sm text-ink"><time dateTime={trip.created_at}>{tripDate(trip.created_at)}</time></div>
          <p className="mt-1 text-xs text-ink-soft">{trip.completed_stops}/{trip.total_stops} {copy.stops} · {Math.round(trip.completion_ratio * 100)}%</p>
        </div>
        <div className="flex justify-end">
          {memoirs[trip.trip_id] ? <button type="button" onClick={() => navigate(`/profile/memoirs/${encodeURIComponent(memoirs[trip.trip_id].memoir_id)}`)} className="min-h-10 whitespace-nowrap rounded-full border border-sage-deep px-4 py-2 text-xs font-medium text-sage-deep transition-colors hover:bg-sage-deep hover:text-paper">{copy.viewMemoir}</button> : trip.completed_stops > 0 ? <button type="button" disabled={Boolean(creatingTrip)} onClick={() => void startMemoir(trip.trip_id)} className="min-h-10 whitespace-nowrap rounded-full bg-sage-deep px-4 py-2 text-xs font-medium text-paper transition-opacity disabled:opacity-50">{creatingTrip === trip.trip_id ? copy.creating : copy.createMemoir}</button> : <span className="max-w-40 text-right text-xs leading-relaxed text-ink-soft">{copy.needCheckin}</span>}
        </div>
      </div>)}
    </div> : null}
    {favorites.length > 0 ? <div className="mt-5"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-sage-deep">{copy.favorite}</p>
      <ul className="mt-2 space-y-2">{favorites.map((item) => <li key={item.poi_id} className="flex justify-between gap-3 text-sm text-ink"><span>{item.poi_name}</span><button type="button" onClick={() => void remove(item.poi_id)} className="text-xs text-clay">{copy.remove}</button></li>)}</ul>
    </div> : null}
  </section>;
}
