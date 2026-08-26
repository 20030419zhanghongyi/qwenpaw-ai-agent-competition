import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { getSharedMemoir, publicAssetUrl, type SharedMemoir } from "@/api/memoirs";
import { postcardImageSrc } from "@/api/postcards";
import {
  localizedMemoirChapterBody,
  localizedMemoirClosing,
  localizedMemoirIntroduction,
  localizedMemoirTitle,
} from "@/lib/memoirLocalization";
import { localizedPoiIdName } from "@/lib/poiLocalization";

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
  const memoirLanguage = memoir.language as keyof typeof PUBLIC_COPY;
  const copy = PUBLIC_COPY[memoirLanguage] ?? PUBLIC_COPY["zh-CN"];
  const cover = memoir.cover_photo_id ? memoir.photos.find((photo) => photo.photo_id === memoir.cover_photo_id) : null;
  return (
    <main className="min-h-dvh bg-paper pb-16 text-ink">
      <header className="border-b border-line">
        <div className="mx-auto max-w-3xl px-5 py-10 sm:py-14">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-sage-deep">
            {copy.label}
          </p>
          <h1 className="mt-3 max-w-2xl font-display text-3xl leading-tight sm:text-4xl">
            {localizedMemoirTitle(memoir.title, memoirLanguage)}
          </h1>
          {memoir.travel_date ? (
            <p className="mt-3 text-xs text-ink-soft">
              {new Date(memoir.travel_date).toLocaleDateString(memoir.language)}
            </p>
          ) : null}
          <p className="mt-6 max-w-2xl text-base leading-7 text-ink-soft">
            {localizedMemoirIntroduction(memoir.introduction, memoirLanguage)}
          </p>
        </div>
      </header>

      <div className="mx-auto max-w-3xl px-5">
        {cover ? (
          <img
            src={publicAssetUrl(cover.image_url)}
            alt=""
            className="mt-8 aspect-[16/9] w-full border border-line object-cover"
          />
        ) : null}

        <div className="divide-y divide-line">
          {memoir.chapters.map((chapter, index) => {
            const chapterName = localizedPoiIdName(
              chapter.poi_id,
              memoirLanguage,
              chapter.poi_name,
            );
            return (
              <article key={chapter.poi_id} className="py-10">
                <p className="text-xs font-semibold tracking-[0.18em] text-sage-deep">
                  {String(index + 1).padStart(2, "0")}
                </p>
                <h2 className="mt-2 font-display text-2xl sm:text-3xl">{chapterName}</h2>
                {chapter.postcard_image_url ? (
                  <img
                    src={postcardImageSrc(chapter.postcard_image_url)}
                    alt=""
                    className="mt-6 aspect-[4/3] w-full border border-line bg-paper-warm object-contain"
                  />
                ) : null}
                <p className="mt-5 whitespace-pre-wrap text-base leading-8">
                  {localizedMemoirChapterBody(
                    chapter.body,
                    memoir.style,
                    index + 1,
                    chapterName,
                    memoirLanguage,
                  )}
                </p>
                {chapter.personal_note ? (
                  <blockquote className="mt-5 border-l-2 border-sage pl-4 text-sm italic leading-7 text-ink-soft">
                    {chapter.personal_note}
                  </blockquote>
                ) : null}
                {(photos[chapter.poi_id] ?? []).map((photo) => (
                  <img
                    key={photo.photo_id}
                    src={publicAssetUrl(photo.image_url)}
                    alt=""
                    className="mt-6 max-h-[32rem] w-full border border-line object-cover"
                  />
                ))}
              </article>
            );
          })}
        </div>

        <footer className="border-t border-sage-deep py-10">
          <p className="font-display text-2xl">{copy.closing}</p>
          <p className="mt-4 whitespace-pre-wrap leading-8 text-ink-soft">
            {localizedMemoirClosing(memoir.closing, memoirLanguage)}
          </p>
        </footer>
        <p className="border-t border-line pt-6 text-xs leading-6 text-ink-soft">
          {copy.privacy}
        </p>
      </div>
    </main>
  );
}
