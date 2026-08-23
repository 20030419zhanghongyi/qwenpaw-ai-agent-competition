import { useState } from "react";
import type { StoryKnowledgeCardData } from "../types";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { SourceBadge } from "./SourceBadge";
import { useStoryMessages } from "../storyI18n";

const KIND_LABELS: Record<string, string> = {
  historical_fact: "史实",
  folklore: "民间信俗／地方记忆",
  contextual_reconstruction: "语境化重建",
  fictional_story: "剧情虚构",
  dynamic_operational_info: "动态营运信息",
};

interface KnowledgeCardProps {
  card: StoryKnowledgeCardData;
  defaultOpen?: boolean;
}

export function KnowledgeCard({
  card,
  defaultOpen = false,
}: KnowledgeCardProps) {
  const st = useStoryMessages();
  const [open, setOpen] = useState(defaultOpen);
  const body = card.text ?? card.content ?? "";
  const panelId = `story-knowledge-${card.id ?? card.title.replace(/\s+/g, "-")}`;

  return (
    <article className="rounded-2xl border border-line bg-card shadow-[var(--shadow-soft)]">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
        className="flex min-h-12 w-full items-center justify-between gap-3 px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sage"
      >
        <span className="min-w-0">
          {card.kind && (
            <span className="block text-[11px] font-semibold tracking-[0.08em] text-sage-deep">
              {KIND_LABELS[card.kind] ?? card.kind}
            </span>
          )}
          <span className="block text-base font-medium text-ink">{card.title}</span>
          {!open && body && (
            <span className="mt-1 line-clamp-2 block text-sm leading-6 text-ink-soft">
              {body}
            </span>
          )}
          {!open && (card.source_label || card.confidence != null) && (
            <span className="mt-2 flex flex-wrap gap-2">
              <SourceBadge label={card.source_label} />
              <ConfidenceBadge confidence={card.confidence} />
            </span>
          )}
        </span>
        <span className="shrink-0 text-[13px] text-sage-deep">
          {open ? st("hideHistory") : st("knowledgeCards")}
        </span>
      </button>
      {open && (
        <div id={panelId} className="border-t border-line px-4 py-4">
          <p className="text-base leading-7 text-ink-soft">{body}</p>
          {(card.source_label || card.confidence != null) && (
            <div className="mt-3 flex flex-wrap gap-2">
              <SourceBadge label={card.source_label} />
              <ConfidenceBadge confidence={card.confidence} />
            </div>
          )}
        </div>
      )}
    </article>
  );
}
