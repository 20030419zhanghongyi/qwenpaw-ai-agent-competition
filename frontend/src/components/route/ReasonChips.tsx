export function ReasonChips({ reasons }: { reasons: string[] }) {
  if (reasons.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5" aria-label="match reasons">
      {reasons.map((r) => (
        <span
          key={r}
          className="rounded-md bg-sage-deep/[0.06] px-2.5 py-1 text-[11px] leading-snug text-moss"
        >
          {r}
        </span>
      ))}
    </div>
  );
}
