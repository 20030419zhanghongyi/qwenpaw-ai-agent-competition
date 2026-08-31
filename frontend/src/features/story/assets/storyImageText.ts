import type { LanguageCode } from "@/types";
import { LOTUS_IMAGE_TEXT_COMMON } from "./lotusImageTextCommon";
import { LOTUS_IMAGE_TEXT_EARLY } from "./lotusImageTextEarly";
import { LOTUS_IMAGE_TEXT_LATE } from "./lotusImageTextLate";

/** Visible lettering only; story summaries and puzzle rules remain in the story API. */
export const STORY_IMAGE_TEXT = {
  ...LOTUS_IMAGE_TEXT_COMMON,
  ...LOTUS_IMAGE_TEXT_EARLY,
  ...LOTUS_IMAGE_TEXT_LATE,
};

export function resolveStoryImageText(
  assetId: string,
  language: LanguageCode,
): readonly string[] | undefined {
  return STORY_IMAGE_TEXT[assetId]?.[language];
}
