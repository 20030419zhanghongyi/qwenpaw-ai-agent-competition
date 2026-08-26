import type { LanguageCode } from "@/types";

export type StoryId = "lotus_city_double_map" | "taipa_letters" | "coloane_after_tide";

const STORY_TITLES: Record<LanguageCode, Record<StoryId, string>> = {
  "zh-CN": {
    lotus_city_double_map: "莲城双图：未尽之图",
    taipa_letters: "海风寄来的信",
    coloane_after_tide: "潮退之后",
  },
  "zh-TW": {
    lotus_city_double_map: "蓮城雙圖：未盡之圖",
    taipa_letters: "海風寄來的信",
    coloane_after_tide: "潮退之後",
  },
  en: {
    lotus_city_double_map: "Two Maps of the Lotus City",
    taipa_letters: "Letters Carried by the Sea Breeze",
    coloane_after_tide: "After the Tide",
  },
  pt: {
    lotus_city_double_map: "Dois Mapas da Cidade de Lótus",
    taipa_letters: "Cartas trazidas pela brisa do mar",
    coloane_after_tide: "Depois da Maré",
  },
};

const STORY_ROUTE_IDS: Record<StoryId, string> = {
  lotus_city_double_map: "lotus_city_double_map",
  taipa_letters: "taipa_hotspot_halfday",
  coloane_after_tide: "coloane_leisure_halfday",
};

export function isStoryId(value: string | null | undefined): value is StoryId {
  return value != null && value in STORY_ROUTE_IDS;
}

export function localizedStoryTitle(storyId: StoryId, language: LanguageCode): string {
  return STORY_TITLES[language][storyId];
}

export function storyUsesRoute(storyId: StoryId, routeId: string | undefined): boolean {
  return routeId === STORY_ROUTE_IDS[storyId];
}
