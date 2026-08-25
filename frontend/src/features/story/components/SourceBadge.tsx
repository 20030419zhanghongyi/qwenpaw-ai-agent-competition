import { useStoryMessages } from "../storyI18n";

export function SourceBadge({ label }: { label?: string }) {
  const st = useStoryMessages();
  if (!label) return null;
  return (
    <span className="inline-flex min-h-6 items-center rounded-full border border-line bg-paper-warm px-2.5 text-[11px] font-medium text-ink-soft">
      {st("source", { label })}
    </span>
  );
}
