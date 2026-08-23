export function SourceBadge({ label }: { label?: string }) {
  if (!label) return null;
  return (
    <span className="inline-flex min-h-6 items-center rounded-full border border-line bg-paper-warm px-2.5 text-[11px] font-medium text-ink-soft">
      来源：{label}
    </span>
  );
}
