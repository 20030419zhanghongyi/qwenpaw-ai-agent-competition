import { useWalk } from "@/state/WalkContext";
import { StoryImage, type StoryImageProps } from "./StoryImage";
import { StoryImageCaption } from "./StoryImageCaption";
import { resolveStoryImageText } from "./storyImageText";

/** Full-size narrative images. Compact thumbnails and layered artwork use StoryImage. */
export function StoryFigure(props: StoryImageProps) {
  const { language } = useWalk();
  if (!resolveStoryImageText(props.assetId, language)?.length) {
    return <StoryImage {...props} />;
  }

  return (
    <figure className="min-w-0">
      <StoryImage {...props} />
      <StoryImageCaption assetId={props.assetId} />
    </figure>
  );
}
