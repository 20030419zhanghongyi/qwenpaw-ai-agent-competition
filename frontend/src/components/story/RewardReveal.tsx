import { useEffect, useRef } from "react";
import { StoryImage } from "@/features/story/assets";
import { CompleteFlowerReveal } from "@/features/story/components/CompleteFlowerReveal";
import { PetalProgress } from "@/features/story/components/PetalProgress";
import type { StoryReward } from "@/types/stories";

interface RewardRevealProps {
  rewards: StoryReward[];
  onDismiss: () => void;
  dismissLabel?: string;
}

const KIND_LABELS: Record<string, { label: string; icon: string }> = {
  stamp: { label: "印记", icon: "🦭" },
  capability: { label: "能力", icon: "🔍" },
  coordinate: { label: "坐标", icon: "📍" },
  story_prop: { label: "故事道具", icon: "⌑" },
  note_petal: { label: "密笺花瓣", icon: "✦" },
  collection: { label: "完整收藏", icon: "❀" },
  reflection: { label: "今日补记", icon: "◇" },
};

function rewardLabel(kind: string): { label: string; icon: string } {
  return KIND_LABELS[kind] ?? { label: kind, icon: "✦" };
}

function petalNumber(id: string): number {
  const match = id.match(/(\d+)$/);
  return match ? Number(match[1]) : 0;
}

function rewardAssetId(reward: StoryReward): string | null {
  if (reward.kind === "note_petal") {
    const assets = [
      "V4-AMA-05",
      "V4-MAN-06",
      "V4-SEN-05",
      "V4-SAM-06",
      "V4-LOU-05",
    ];
    return assets[petalNumber(reward.id) - 1] ?? null;
  }
  if (reward.id === "complete_city_flower" || reward.kind === "collection") {
    return "V4-FOR-08";
  }
  if (reward.id === "research_materials") return "V4-PROP-03";
  return null;
}

export function RewardReveal({
  rewards,
  onDismiss,
  dismissLabel = "收下并查看下一站",
}: RewardRevealProps) {
  const dismissRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (rewards.length === 0) return;
    dismissRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onDismiss();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [rewards.length, onDismiss]);

  if (rewards.length === 0) return null;
  const petals = rewards.filter((reward) => reward.kind === "note_petal");

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink/40 px-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="story-reward-title"
      style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}
    >
      <div className="w-full max-w-sm rounded-3xl border border-line bg-paper p-6 shadow-[var(--shadow-lift)] motion-safe:animate-[fadeIn_.3s_ease-out]">
        <p className="text-center text-xs font-semibold uppercase tracking-[0.22em] text-sage-deep">
          章节收获
        </p>
        <h2 id="story-reward-title" className="sr-only">获得故事奖励</h2>

        <div className="mt-5 space-y-4">
          {rewards.map((reward) => {
            const meta = rewardLabel(reward.kind);
            const assetId = rewardAssetId(reward);
            const completesFlower =
              reward.kind === "note_petal" && petalNumber(reward.id) === 5;
            return (
              <div
                key={reward.id}
                className="rounded-2xl border border-line bg-paper-warm p-4 text-center"
              >
                {assetId ? (
                  <StoryImage
                    assetId={assetId}
                    alt={reward.name ?? meta.label}
                    eager
                    className="mx-auto w-28 border-0 bg-transparent"
                    imageClassName="object-contain"
                  />
                ) : (
                  <span className="text-3xl" aria-hidden>{meta.icon}</span>
                )}
                <p className="mt-2 font-serif text-lg font-semibold text-ink">
                  {reward.name ?? reward.id}
                </p>
                <p className="mt-0.5 text-xs text-ink-soft">{meta.label}</p>
                {reward.text && (
                  <p className="mt-2 text-base leading-7 text-ink-soft">
                    {reward.text}
                  </p>
                )}
                {completesFlower && (
                  <div className="mt-4 border-t border-line pt-4">
                    <CompleteFlowerReveal />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {petals.length > 0 && (
          <div className="mt-4 flex justify-center">
            <PetalProgress
              collected={petalNumber(petals[petals.length - 1].id)}
            />
          </div>
        )}

        <button
          ref={dismissRef}
          type="button"
          onClick={onDismiss}
          className="mt-5 min-h-12 w-full rounded-full bg-sage-deep px-5 text-base font-medium text-paper shadow-[var(--shadow-soft)] transition active:scale-[0.99]"
        >
          {dismissLabel}
        </button>
      </div>
    </div>
  );
}
