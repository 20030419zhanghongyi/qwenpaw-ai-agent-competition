import { useStoryMessages } from "../storyI18n";

function confidenceLabel(
  confidence: number | string,
  st: ReturnType<typeof useStoryMessages>,
): string {
  if (typeof confidence === "string") {
    const labels: Record<string, string> = {
      high: st("confidenceHigh"),
      medium: st("confidenceMedium"),
      low: st("confidenceLow"),
    };
    return labels[confidence.toLowerCase()] ?? confidence;
  }
  return `${Math.round(Math.max(0, Math.min(1, confidence)) * 100)}%`;
}

export function ConfidenceBadge({
  confidence,
}: {
  confidence?: number | string;
}) {
  const st = useStoryMessages();
  if (confidence == null) return null;
  return (
    <span className="inline-flex min-h-6 items-center rounded-full border border-sage/30 bg-sage/10 px-2.5 text-[11px] font-medium text-sage-deep">
      {st("confidence", { value: confidenceLabel(confidence, st) })}
    </span>
  );
}
