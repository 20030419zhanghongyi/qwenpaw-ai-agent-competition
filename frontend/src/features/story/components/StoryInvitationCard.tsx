import { StoryImage } from "../assets";
import { STORY_CATALOG } from "@/story-discovery/storyCatalog";
import { useStoryMessages } from "../storyI18n";

interface StoryInvitationCardProps {
  storyId: string;
  onAccept: () => void;
  onDecline: () => void;
}

export function StoryInvitationCard({
  storyId,
  onAccept,
  onDecline,
}: StoryInvitationCardProps) {
  const st = useStoryMessages();
  const story = STORY_CATALOG.find((entry) => entry.storyId === storyId);
  const isColoane = storyId === "coloane_after_tide";
  const isTaipa = storyId === "taipa_letters";
  const invitationAssetId = isColoane
    ? "CAT-COVER-01"
    : isTaipa
      ? "TAI-COVER-01"
      : "V4-ENTRY-01";
  const title = story?.title ?? st("macauStory");

  return (
    <section
      aria-labelledby="story-invitation-title"
      className="mb-10 overflow-hidden rounded-3xl border border-ochre/30 bg-card shadow-[var(--shadow-lift)]"
    >
      <StoryImage
        assetId={invitationAssetId}
        alt={st("storyInvitation", { title })}
        eager
        className="rounded-none border-0"
      />
      <div className="p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-ochre">
          {isColoane
            ? st("coloaneAudioStory")
            : isTaipa
              ? st("taipaLetterStory")
              : st("limitedStory")}
        </p>
        <h2
          id="story-invitation-title"
          className="mt-2 font-display text-2xl leading-tight text-ink"
        >
          {title}
        </h2>
        <p className="mt-3 text-base leading-7 text-ink-soft">
          {story?.subtitle ?? st("invitationBody")}
        </p>
        <div className="mt-5 grid gap-2">
          <button
            type="button"
            onClick={onAccept}
            className="min-h-12 w-full rounded-full bg-sage-deep px-5 text-base font-medium text-paper shadow-[var(--shadow-soft)]"
          >
            {st("enterStory", { title })}
          </button>
          <button
            type="button"
            onClick={onDecline}
            className="min-h-12 w-full rounded-full border border-line bg-paper px-5 text-base font-medium text-ink"
          >
            {st("continuePlanner")}
          </button>
        </div>
      </div>
    </section>
  );
}
