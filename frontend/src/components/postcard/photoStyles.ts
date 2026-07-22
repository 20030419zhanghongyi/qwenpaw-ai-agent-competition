import type { MessageKey } from "@/i18n";
import type { PhotoStyle } from "@/types/postcards";

export const PHOTO_STYLE_OPTIONS: ReadonlyArray<{
  value: PhotoStyle;
  labelKey: MessageKey;
}> = [
  { value: "souvenir", labelKey: "postcardPhotoStyleSouvenir" },
  { value: "watercolor", labelKey: "postcardPhotoStyleWatercolor" },
  { value: "azulejo", labelKey: "postcardPhotoStyleAzulejo" },
  { value: "vintage", labelKey: "postcardPhotoStyleVintage" },
  { value: "ink", labelKey: "postcardPhotoStyleInk" },
];

export function photoStyleLabelKey(style: PhotoStyle | null | undefined): MessageKey {
  return (
    PHOTO_STYLE_OPTIONS.find((option) => option.value === style)?.labelKey ??
    "postcardPhotoStyleSouvenir"
  );
}
