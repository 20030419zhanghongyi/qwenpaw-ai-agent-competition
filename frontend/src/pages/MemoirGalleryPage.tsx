import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  getTripMemoir,
  loadPrivatePhoto,
  type MemoirPhoto,
  type TravelMemoir,
} from "@/api/memoirs";
import { listTripHistory } from "@/api/profile";
import { AzulejoBand } from "@/components/brand/AzulejoBand";
import { ErrorState, LoadingState } from "@/components/common/States";
import { ProfileSidebar } from "@/components/profile/ProfileSidebar";
import { TravelHistoryPanel } from "@/components/profile/TravelHistoryPanel";
import { useAuth } from "@/state/AuthContext";
import { useWalk } from "@/state/WalkContext";

const COPY = {
  "zh-CN": {
    eyebrow: "个人中心 · Memories",
    title: "个人回忆录",
    lead: "把你在澳门各个地方上传的照片收在一起，按旅程和地点重新翻阅。",
    signInTitle: "登录后查看你的回忆录",
    signInLead: "照片属于你的私人旅行记录，登录后才能读取和管理。",
    signIn: "登录",
    loading: "正在整理旅行照片…",
    error: "无法载入个人回忆录",
    retry: "重试",
    emptyTitle: "回忆录还是空的",
    emptyLead: "完成一次地点打卡并创建旅行回忆录，就可以上传第一张照片。",
    backProfile: "规划新行程",
    photos: "张照片",
    memoirs: "本回忆录",
    edit: "打开回忆录",
    unassigned: "未关联地点",
    people: "含人物",
    private: "这些照片默认仅你可见；只有主动创建分享链接后才会公开隐私裁剪版本。",
  },
  "zh-TW": {
    eyebrow: "個人中心 · Memories",
    title: "個人回憶錄",
    lead: "把你在澳門各個地方上傳的照片收在一起，按旅程和地點重新翻閱。",
    signInTitle: "登入後查看你的回憶錄",
    signInLead: "照片屬於你的私人旅行記錄，登入後才能讀取和管理。",
    signIn: "登入",
    loading: "正在整理旅行照片…",
    error: "無法載入個人回憶錄",
    retry: "重試",
    emptyTitle: "回憶錄還是空的",
    emptyLead: "完成一次地點打卡並建立旅行回憶錄，就可以上傳第一張照片。",
    backProfile: "規劃新行程",
    photos: "張照片",
    memoirs: "本回憶錄",
    edit: "打開回憶錄",
    unassigned: "未關聯地點",
    people: "含人物",
    private: "這些照片預設只有你可見；只有主動建立分享連結後才會公開隱私裁剪版本。",
  },
  en: {
    eyebrow: "Profile · Memories",
    title: "Personal memoir",
    lead: "Bring together the photos you uploaded around Macau, then revisit them by trip and place.",
    signInTitle: "Sign in to see your memoir",
    signInLead: "These photos are part of your private travel record and require your account to view or manage.",
    signIn: "Sign in",
    loading: "Gathering your travel photos…",
    error: "Unable to load your memoir",
    retry: "Try again",
    emptyTitle: "Your memoir is still empty",
    emptyLead: "Check in at a place and create a travel memoir to upload your first photo.",
    backProfile: "Plan a new itinerary",
    photos: "photos",
    memoirs: "memoirs",
    edit: "Open memoir",
    unassigned: "No place assigned",
    people: "People in photo",
    private: "Photos are visible only to you by default. A privacy-filtered version appears only after you create a share link.",
  },
  pt: {
    eyebrow: "Perfil · Memórias",
    title: "Memórias pessoais",
    lead: "Reúna as fotografias carregadas em Macau e volte a vê-las por viagem e por local.",
    signInTitle: "Inicie sessão para ver as suas memórias",
    signInLead: "Estas fotografias fazem parte do seu registo privado e requerem a sua conta para consulta ou gestão.",
    signIn: "Iniciar sessão",
    loading: "A organizar as fotografias da viagem…",
    error: "Não foi possível carregar as memórias",
    retry: "Tentar novamente",
    emptyTitle: "As suas memórias ainda estão vazias",
    emptyLead: "Faça check-in num local e crie memórias de viagem para carregar a primeira fotografia.",
    backProfile: "Planear um novo itinerário",
    photos: "fotografias",
    memoirs: "memórias",
    edit: "Abrir memórias",
    unassigned: "Sem local associado",
    people: "Pessoas na fotografia",
    private: "As fotografias são privadas por predefinição. Só é mostrada uma versão protegida depois de criar uma ligação de partilha.",
  },
} as const;

interface GalleryPhoto {
  memoir: TravelMemoir;
  photo: MemoirPhoto;
  url: string;
  placeName: string;
}

export function MemoirGalleryPage() {
  const { language } = useWalk();
  const { isAuthenticated, token, userId } = useAuth();
  const copy = COPY[language];
  const [memoirs, setMemoirs] = useState<TravelMemoir[]>([]);
  const [photos, setPhotos] = useState<GalleryPhoto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!token || !userId) {
      setLoading(false);
      setMemoirs([]);
      setPhotos([]);
      return;
    }

    let cancelled = false;
    const objectUrls: string[] = [];
    setLoading(true);
    setError(null);

    void listTripHistory(userId)
      .then((trips) =>
        Promise.all(
          trips.map(async (trip) => {
            try {
              return await getTripMemoir(trip.trip_id, token);
            } catch {
              return null;
            }
          }),
        ),
      )
      .then(async (items) => {
        const available = items.filter(
          (item): item is TravelMemoir => item !== null,
        );
        const loaded = await Promise.all(
          available.flatMap((memoir) =>
            memoir.photos.map(async (photo) => {
              const url = await loadPrivatePhoto(photo, memoir.memoir_id, token);
              objectUrls.push(url);
              const placeName =
                memoir.chapters.find((chapter) => chapter.poi_id === photo.poi_id)
                  ?.poi_name ?? copy.unassigned;
              return { memoir, photo, url, placeName };
            }),
          ),
        );
        if (cancelled) {
          loaded.forEach(({ url }) => URL.revokeObjectURL(url));
          return;
        }
        setMemoirs(available);
        setPhotos(
          loaded.sort(
            (left, right) =>
              new Date(right.photo.created_at).getTime() -
              new Date(left.photo.created_at).getTime(),
          ),
        );
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : copy.error);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [copy.error, copy.unassigned, reloadKey, token, userId]);

  const memoirPhotoCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    photos.forEach(({ memoir }) => {
      counts[memoir.memoir_id] = (counts[memoir.memoir_id] ?? 0) + 1;
    });
    return counts;
  }, [photos]);

  return (
    <main className="relative flex-1 bg-paper pb-24">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-[radial-gradient(ellipse_at_top,_oklch(0.62_0.038_145_/_0.12),_transparent_65%)]"
      />
      <div className="relative mx-auto max-w-6xl px-5 pt-8 lg:px-8">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-sage-deep">
          {copy.eyebrow}
        </p>
        <h1 className="mb-2 font-display text-3xl leading-tight text-ink lg:text-4xl">
          {copy.title}
        </h1>
        <p className="mb-8 max-w-xl text-sm leading-relaxed text-ink-soft">
          {copy.lead}
        </p>

        <div className="grid min-w-0 gap-8 lg:grid-cols-[13rem_minmax(0,1fr)]">
          <ProfileSidebar language={language} />
          <div className="min-w-0">
            {!isAuthenticated ? (
              <section className="rounded-[1.75rem] border border-line bg-card px-6 py-10 text-center shadow-[var(--shadow-soft)]">
                <h2 className="font-display text-2xl text-ink">{copy.signInTitle}</h2>
                <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-soft">
                  {copy.signInLead}
                </p>
                <Link
                  to="/auth?returnTo=%2Fprofile%2Fmemories"
                  className="mt-6 inline-flex rounded-full bg-sage-deep px-6 py-3 text-sm font-medium text-paper transition hover:bg-moss"
                >
                  {copy.signIn}
                </Link>
              </section>
            ) : null}

            {isAuthenticated ? (
              <TravelHistoryPanel
                userId={userId}
                token={token}
                language={language}
              />
            ) : null}

            {isAuthenticated && loading ? <LoadingState label={copy.loading} /> : null}
            {isAuthenticated && !loading && error ? (
              <ErrorState
                title={copy.error}
                message={error}
                onRetry={() => setReloadKey((value) => value + 1)}
                retryLabel={copy.retry}
              />
            ) : null}

            {isAuthenticated && !loading && !error && photos.length === 0 ? (
              <section className="rounded-[1.75rem] border border-line bg-card px-6 py-10 text-center shadow-[var(--shadow-soft)]">
                <h2 className="font-display text-2xl text-ink">{copy.emptyTitle}</h2>
                <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-soft">
                  {copy.emptyLead}
                </p>
                <Link
                  to="/preferences"
                  className="mt-6 inline-flex rounded-full border border-sage-deep px-5 py-2.5 text-sm font-medium text-sage-deep transition hover:bg-sage-deep hover:text-paper"
                >
                  {copy.backProfile}
                </Link>
              </section>
            ) : null}

            {isAuthenticated && !loading && !error && photos.length > 0 ? (
              <>
                <section className="mb-7 flex flex-wrap items-end justify-between gap-4 rounded-2xl border border-line bg-card px-5 py-4 shadow-[var(--shadow-soft)]">
                  <div>
                    <p className="font-display text-2xl text-ink">{photos.length}</p>
                    <p className="text-xs text-ink-soft">{copy.photos}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-display text-2xl text-ink">{memoirs.length}</p>
                    <p className="text-xs text-ink-soft">{copy.memoirs}</p>
                  </div>
                </section>

                <AzulejoBand className="mb-7" />

                <div className="columns-1 gap-5 sm:columns-2 xl:columns-3">
                  {photos.map(({ memoir, photo, url, placeName }) => (
                    <article
                      key={photo.photo_id}
                      className="mb-5 break-inside-avoid overflow-hidden rounded-2xl border border-line bg-card shadow-[var(--shadow-soft)]"
                    >
                      <img
                        src={url}
                        alt={placeName}
                        className="max-h-[28rem] w-full object-cover"
                      />
                      <div className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-ink">{placeName}</p>
                            <p className="mt-1 truncate text-xs text-ink-soft">
                              {memoir.title}
                            </p>
                          </div>
                          {photo.has_people ? (
                            <span className="shrink-0 rounded-full bg-paper-warm px-2 py-1 text-[10px] text-ink-soft">
                              {copy.people}
                            </span>
                          ) : null}
                        </div>
                        <div className="mt-3 flex items-center justify-between gap-3 border-t border-line/70 pt-3">
                          <span className="text-[11px] text-ink-soft">
                            {new Date(photo.created_at).toLocaleDateString(language)}
                          </span>
                          <Link
                            to={`/profile/memoirs/${encodeURIComponent(memoir.memoir_id)}`}
                            className="text-xs font-medium text-sage-deep hover:underline"
                          >
                            {copy.edit}
                          </Link>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>

                <p className="mt-3 rounded-2xl bg-paper-warm px-5 py-4 text-xs leading-relaxed text-ink-soft">
                  {copy.private}
                </p>

                {memoirs.some((memoir) => !memoirPhotoCounts[memoir.memoir_id]) ? (
                  <div className="mt-5 flex flex-wrap gap-2">
                    {memoirs
                      .filter((memoir) => !memoirPhotoCounts[memoir.memoir_id])
                      .map((memoir) => (
                        <Link
                          key={memoir.memoir_id}
                          to={`/profile/memoirs/${encodeURIComponent(memoir.memoir_id)}`}
                          className="rounded-full border border-line bg-card px-4 py-2 text-xs text-ink transition hover:border-sage"
                        >
                          {memoir.title} · {copy.edit}
                        </Link>
                      ))}
                  </div>
                ) : null}
              </>
            ) : null}

          </div>
        </div>
      </div>
    </main>
  );
}
