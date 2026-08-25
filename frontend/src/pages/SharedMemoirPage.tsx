import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { getSharedMemoir, publicAssetUrl, type SharedMemoir } from "@/api/memoirs";
import { postcardImageSrc } from "@/api/postcards";

const PUBLIC_COPY = {
  "zh-CN": { label: "澳门 · 旅行回忆录", closing: "旅程结语", privacy: "这是一份由旅行者主动分享、经过隐私设置裁剪的回忆录。" },
  "zh-TW": { label: "澳門 · 旅行回憶錄", closing: "旅程結語", privacy: "這是一份由旅行者主動分享、經過隱私設定裁剪的回憶錄。" },
  en: { label: "Macau · Travel memoir", closing: "Journey closing", privacy: "This memoir was shared by its traveler and filtered using their privacy choices." },
  pt: { label: "Macau · Memórias de viagem", closing: "Conclusão da viagem", privacy: "Estas memórias foram partilhadas pelo viajante e filtradas pelas suas opções de privacidade." },
} as const;

export function SharedMemoirPage() {
  const { shareToken = "" } = useParams();
  const [memoir, setMemoir] = useState<SharedMemoir | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { void getSharedMemoir(shareToken).then(setMemoir).catch((err: unknown) => setError(err instanceof Error ? err.message : "Unable to open memoir")); }, [shareToken]);
  const photos = useMemo(() => {
    const result: Record<string, SharedMemoir["photos"]> = {};
    for (const photo of memoir?.photos ?? []) (result[photo.poi_id ?? "unassigned"] ??= []).push(photo);
    return result;
  }, [memoir?.photos]);
  if (error) return <main className="flex min-h-dvh items-center justify-center bg-paper px-5"><div className="max-w-md rounded-2xl border border-line bg-card p-8 text-center"><h1 className="font-display text-2xl text-ink">这条回忆链接已失效</h1><p className="mt-3 text-sm text-ink-soft">{error}</p></div></main>;
  if (!memoir) return <main className="flex min-h-dvh items-center justify-center bg-paper text-sm text-ink-soft">Loading memoir…</main>;
  const copy = PUBLIC_COPY[memoir.language as keyof typeof PUBLIC_COPY] ?? PUBLIC_COPY["zh-CN"];
  const cover = memoir.cover_photo_id ? memoir.photos.find((photo) => photo.photo_id === memoir.cover_photo_id) : null;
  return <main className="min-h-dvh bg-paper pb-20"><header className="mx-auto max-w-4xl overflow-hidden bg-card sm:mt-8 sm:rounded-[2.5rem] sm:border sm:border-line sm:shadow-[var(--shadow-soft)]">{cover ? <img src={publicAssetUrl(cover.image_url)} alt="" className="h-[42vh] min-h-72 w-full object-cover" /> : <div className="h-64 bg-gradient-to-br from-sage-deep/25 via-paper-warm to-clay/15" />}<div className="px-6 py-8 sm:px-10"><p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-sage-deep">{copy.label}</p><h1 className="mt-3 font-display text-4xl leading-tight text-ink sm:text-5xl">{memoir.title}</h1><div className="mt-4 flex flex-wrap gap-3 text-xs text-ink-soft">{memoir.travel_date ? <span>{new Date(memoir.travel_date).toLocaleDateString(memoir.language)}</span> : null}{memoir.route_id ? <span>{memoir.route_id}</span> : null}</div><p className="mt-6 max-w-2xl text-base leading-8 text-ink-soft">{memoir.introduction}</p></div></header><div className="mx-auto mt-10 max-w-3xl space-y-10 px-5">{memoir.chapters.map((chapter, index) => <article key={chapter.poi_id} className="rounded-[1.75rem] border border-line bg-card p-6 shadow-[var(--shadow-soft)]"><p className="text-xs font-semibold tracking-[0.18em] text-sage-deep">{String(index + 1).padStart(2, "0")}</p><h2 className="mt-2 font-display text-3xl text-ink">{chapter.poi_name}</h2>{chapter.postcard_image_url ? <img src={postcardImageSrc(chapter.postcard_image_url)} alt="" className="mt-5 max-h-[28rem] w-full rounded-2xl object-cover" /> : null}<p className="mt-5 whitespace-pre-wrap text-base leading-8 text-ink">{chapter.body}</p>{chapter.personal_note ? <blockquote className="mt-5 border-l-2 border-sage pl-4 text-sm italic leading-7 text-ink-soft">{chapter.personal_note}</blockquote> : null}{(photos[chapter.poi_id] ?? []).map((photo) => <img key={photo.photo_id} src={publicAssetUrl(photo.image_url)} alt="" className="mt-5 max-h-[32rem] w-full rounded-2xl object-cover" />)}</article>)}<footer className="rounded-[1.75rem] bg-sage-deep px-7 py-10 text-paper"><p className="font-display text-2xl">{copy.closing}</p><p className="mt-4 whitespace-pre-wrap leading-8 text-paper/85">{memoir.closing}</p></footer><p className="text-center text-xs text-ink-soft">{copy.privacy}</p></div></main>;
}
