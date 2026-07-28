import { useMemo, useState } from "react";
import { postcardImageSrc } from "@/api/postcards";
import type { LanguageCode } from "@/types";
import type { Postcard } from "@/types/postcards";

const COPY = {
  "zh-CN": { title: "本次旅行回忆", lead: "按实际到访顺序串起的可分享旅行回忆册。", share: "分享回忆", copied: "回忆链接已复制" },
  "zh-TW": { title: "本次旅行回憶", lead: "按實際到訪順序串起的可分享旅行回憶冊。", share: "分享回憶", copied: "回憶連結已複製" },
  en: { title: "Your travel memory", lead: "A shareable memory album in your visit order.", share: "Share memory", copied: "Memory link copied" },
  pt: { title: "A sua memória de viagem", lead: "Um álbum partilhável pela ordem das visitas.", share: "Partilhar memória", copied: "Ligação copiada" },
} as const;

export function TravelMemory({ postcards, language }: { postcards: Postcard[]; language: LanguageCode }) {
  const copy = COPY[language];
  const [note, setNote] = useState<string | null>(null);
  const ordered = useMemo(() => [...postcards].sort((a, b) => a.stop_order - b.stop_order), [postcards]);
  if (ordered.length === 0) return null;
  const share = async () => {
    const url = window.location.href;
    const text = ordered.map((card) => `${card.stop_order + 1}. ${card.poi_name}`).join(" → ");
    try {
      if (navigator.share) await navigator.share({ title: copy.title, text, url });
      else { await navigator.clipboard.writeText(url); setNote(copy.copied); }
    } catch { /* User cancellation needs no error state. */ }
  };
  return <section className="mb-8 overflow-hidden rounded-[1.75rem] border border-sage-deep/20 bg-gradient-to-br from-card via-paper-warm to-card px-5 py-6 shadow-[var(--shadow-soft)]">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-sage-deep">{copy.title}</p><p className="mt-1 text-sm text-ink-soft">{copy.lead}</p></div><button type="button" onClick={() => void share()} className="rounded-full border border-sage-deep px-4 py-2 text-xs font-medium text-sage-deep">{copy.share}</button></div>
    <ol className="mt-5 grid gap-3 sm:grid-cols-2">{ordered.map((card, index) => <li key={card.postcard_id} className="flex items-center gap-3 rounded-xl border border-line/70 bg-card/70 p-3"><img src={postcardImageSrc(card.image_url)} alt="" className="h-14 w-16 rounded-lg object-cover"/><div><p className="text-xs text-sage-deep">{index + 1}</p><p className="text-sm font-medium text-ink">{card.poi_name}</p><p className="line-clamp-2 text-xs text-ink-soft">{card.caption}</p></div></li>)}</ol>
    {note ? <p className="mt-3 text-xs text-sage-deep">{note}</p> : null}
  </section>;
}
