import type { StoryKnowledgeCardData } from "../types";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { SourceBadge } from "./SourceBadge";
import { useStoryMessages } from "../storyI18n";

interface KnowledgeCardProps {
  card: StoryKnowledgeCardData;
  defaultOpen?: boolean;
}

export function KnowledgeCard({
  card,
  defaultOpen: _defaultOpen = false,
}: KnowledgeCardProps) {
  const st = useStoryMessages();
  const kindLabels: Record<string, string> = {
    historical_fact: st("kindHistorical"),
    folklore: st("kindFolklore"),
    contextual_reconstruction: st("kindReconstruction"),
    fictional_story: st("kindFiction"),
    dynamic_operational_info: st("kindOperational"),
  };
  const body = card.text ?? card.content ?? "";

  return (
    <article className="rounded-2xl border border-line bg-card px-4 py-4 shadow-[var(--shadow-soft)]">
      {card.kind && (
        <p className="text-[11px] font-semibold tracking-[0.08em] text-sage-deep">
          {kindLabels[card.kind] ?? card.kind}
        </p>
      )}
      <h3 className="mt-1 break-words text-base font-medium text-ink">
        {card.title}
      </h3>
      {body && (
        <p className="mt-3 break-words text-base leading-7 text-ink-soft">
          {body}
        </p>
      )}
      {(card.source_label || card.confidence != null) && (
        <div className="mt-3 flex min-w-0 flex-wrap gap-2">
          <SourceBadge label={card.source_label} />
          <ConfidenceBadge confidence={card.confidence} />
        </div>
      )}
    </article>
  );
}
