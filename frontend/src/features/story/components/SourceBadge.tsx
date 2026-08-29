import { useStoryMessages } from "../storyI18n";

export function SourceBadge({ label }: { label?: string }) {
  const st = useStoryMessages();
  if (!label) return null;
  return (
    <span className="inline-flex min-h-6 max-w-full items-center rounded-full border border-line bg-paper-warm px-2.5 py-1 text-[11px] font-medium leading-4 text-ink-soft">
      {st("source", { label })}
    </span>
  );
}
