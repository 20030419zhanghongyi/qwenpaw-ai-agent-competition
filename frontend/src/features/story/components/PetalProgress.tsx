interface PetalProgressProps {
  collected: number;
  total?: number;
  compact?: boolean;
  label?: string;
}

export function PetalProgress({
  collected,
  total = 5,
  compact = false,
  label = "花瓣进度",
}: PetalProgressProps) {
  const safeTotal = Math.max(1, total);
  const safeCollected = Math.min(Math.max(0, collected), safeTotal);

  return (
    <div
      className="inline-flex items-center gap-2"
      role="img"
      aria-label={`${label}：${safeCollected}/${safeTotal}`}
    >
      <span className="flex gap-1" aria-hidden>
        {Array.from({ length: safeTotal }, (_, index) => (
          <span
            key={index}
            className={`block rounded-[70%_35%_70%_35%] border transition ${
              index < safeCollected
                ? "size-3 rotate-45 border-ochre bg-ochre"
                : "size-3 rotate-45 border-line bg-paper"
            }`}
          />
        ))}
      </span>
      {!compact && (
        <span className="text-xs tabular-nums text-ink-soft">
          {safeCollected}/{safeTotal}
        </span>
      )}
    </div>
  );
}
