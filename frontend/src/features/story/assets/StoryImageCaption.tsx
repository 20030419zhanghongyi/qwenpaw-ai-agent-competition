import { useWalk } from "@/state/WalkContext";
import { useStoryMessages } from "../storyI18n";
import { resolveStoryImageText } from "./storyImageText";

interface StoryImageCaptionProps {
  assetId: string;
  dark?: boolean;
  as?: "figcaption" | "div";
}

export function StoryImageCaption({
  assetId,
  dark = false,
  as: Tag = "figcaption",
}: StoryImageCaptionProps) {
  const { language } = useWalk();
  const st = useStoryMessages();
  const paragraphs = resolveStoryImageText(assetId, language);
  if (!paragraphs?.length) return null;

  return (
    <Tag
      lang={language}
      data-story-image-text={assetId}
      className={`mx-auto mt-3 w-full max-w-prose px-1 text-left ${dark ? "text-paper/90" : "text-ink-soft"}`}
    >
      <p className={`mb-2 text-xs font-medium tracking-wide ${dark ? "text-paper/60" : "text-sage-deep"}`}>
        {st("imageText")}
      </p>
      <div className="space-y-2.5 text-base leading-7 [overflow-wrap:anywhere]">
        {paragraphs.map((paragraph, index) => (
          <p key={index} className="whitespace-pre-line">{paragraph}</p>
        ))}
      </div>
    </Tag>
  );
}
