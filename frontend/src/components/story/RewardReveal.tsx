import type { StoryReward } from "@/types/stories";

interface RewardRevealProps {
  rewards: StoryReward[];
  onDismiss: () => void;
}

const KIND_LABELS: Record<string, { label: string; icon: string }> = {
  stamp: { label: "印记", icon: "🦭" },
  capability: { label: "能力", icon: "🔍" },
  coordinate: { label: "坐标", icon: "📍" },
};

function rewardLabel(kind: string): { label: string; icon: string } {
  return KIND_LABELS[kind] ?? { label: kind, icon: "✦" };
}

export function RewardReveal({ rewards, onDismiss }: RewardRevealProps) {
  if (rewards.length === 0) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/30 px-4 pb-8 sm:items-center">
      <div className="w-full max-w-sm rounded-3xl border border-line bg-paper p-6 shadow-[var(--shadow-lift)] animate-[fadeIn_.3s_ease-out]">
        <p className="text-center text-xs font-semibold uppercase tracking-[0.22em] text-sage-deep">
          获得线索
        </p>

        <div className="mt-5 space-y-4">
          {rewards.map((reward) => {
            const meta = rewardLabel(reward.kind);
            return (
              <div
                key={reward.id}
                className="rounded-2xl border border-line bg-paper-warm p-4 text-center"
              >
                <span className="text-3xl" aria-hidden>
                  {meta.icon}
                </span>
                <p className="mt-2 font-serif text-lg font-semibold text-ink">
                  {reward.name ?? reward.id}
                </p>
                <p className="mt-0.5 text-xs text-ink-soft">{meta.label}</p>
                {reward.text && (
                  <p className="mt-2 text-sm italic text-ink-soft">
                    {reward.text}
                  </p>
                )}
              </div>
            );
          })}
        </div>

        <button
          type="button"
          onClick={onDismiss}
          className="mt-5 w-full rounded-full bg-sage-deep px-5 py-3 text-sm font-medium text-paper shadow-[var(--shadow-soft)] transition hover:bg-moss active:scale-[0.99]"
        >
          收下
        </button>
      </div>
    </div>
  );
}
