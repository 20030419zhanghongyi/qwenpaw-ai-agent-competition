import { StoryImage } from "../assets";

interface StoryInvitationCardProps {
  onAccept: () => void;
  onDecline: () => void;
}

export function StoryInvitationCard({
  onAccept,
  onDecline,
}: StoryInvitationCardProps) {
  return (
    <section
      aria-labelledby="story-invitation-title"
      className="mb-10 overflow-hidden rounded-3xl border border-ochre/30 bg-card shadow-[var(--shadow-lift)]"
    >
      <StoryImage
        assetId="V4-ENTRY-01"
        alt="莲城双图限定故事游邀请"
        eager
        className="rounded-none border-0"
      />
      <div className="p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-ochre">
          限定故事游
        </p>
        <h2
          id="story-invitation-title"
          className="mt-2 font-display text-2xl leading-tight text-ink"
        >
          跟着两张旧地图，重新认识澳门
        </h2>
        <p className="mt-3 text-base leading-7 text-ink-soft">
          一日六站的实地故事，可随时查看提示，也可以跳过谜题继续游览。
        </p>
        <div className="mt-5 grid gap-2">
          <button
            type="button"
            onClick={onAccept}
            className="min-h-12 w-full rounded-full bg-sage-deep px-5 text-base font-medium text-paper shadow-[var(--shadow-soft)]"
          >
            进入《莲城双图》
          </button>
          <button
            type="button"
            onClick={onDecline}
            className="min-h-12 w-full rounded-full border border-line bg-paper px-5 text-base font-medium text-ink"
          >
            继续普通路线规划
          </button>
        </div>
      </div>
    </section>
  );
}
