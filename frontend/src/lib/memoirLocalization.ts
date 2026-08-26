import type { LanguageCode } from "@/types";

const DEFAULT_TITLES: Record<LanguageCode, string> = {
  "zh-CN": "我的澳门旅行回忆",
  "zh-TW": "我的澳門旅行回憶",
  en: "My Macau Travel Memoir",
  pt: "As minhas memórias de Macau",
};

const SYSTEM_TITLES = new Set(Object.values(DEFAULT_TITLES));

const DEFAULT_INTRODUCTIONS: Record<LanguageCode, string> = {
  "zh-CN": "这本回忆录按照真实打卡顺序，记录这次澳门旅程。",
  "zh-TW": "這本回憶錄按照真實打卡順序，記錄這次澳門旅程。",
  en: "This memoir follows the verified check-in order of my Macau trip.",
  pt: "Estas memórias seguem a ordem real dos check-ins da viagem a Macau.",
};

const DEFAULT_CLOSINGS: Record<LanguageCode, string> = {
  "zh-CN": "旅程在这里告一段落，留下的是亲自走过的地点与保存下来的片段。",
  "zh-TW": "旅程在這裡告一段落，留下的是親自走過的地點與保存下來的片段。",
  en: "The route ends here, leaving a record of the places I visited and saved.",
  pt: "O percurso termina aqui, deixando o registo dos lugares visitados.",
};

const SYSTEM_INTRODUCTIONS = new Set(Object.values(DEFAULT_INTRODUCTIONS));
const SYSTEM_CLOSINGS = new Set(Object.values(DEFAULT_CLOSINGS));

const SYSTEM_CHAPTER_PATTERNS = [
  /^我来到了.+。这是本次旅程的第\d+个打卡地点。$/,
  /^第\d+站 · .+。这一章节依据实际到访记录整理。$/,
  /^第\d+站，打卡.+。$/,
  /^行程记录来到第\d+站：.+。$/,
  /^我來到了.+。這是本次旅程的第\d+個打卡地點。$/,
  /^第\d+站 · .+。這一章節依據實際到訪記錄整理。$/,
  /^第\d+站，打卡.+。$/,
  /^行程記錄來到第\d+站：.+。$/,
  /^I arrived at .+, the \d+ stop recorded on this trip\.$/,
  /^Stop \d+ · .+\. This chapter is assembled from the recorded visit\.$/,
  /^Stop \d+: checked in at .+\.$/,
  /^The recorded journey reaches stop \d+: .+\.$/,
  /^Cheguei a .+, a \d+\.ª paragem registada nesta viagem\.$/,
  /^Paragem \d+ · .+\. Este capítulo baseia-se na visita registada\.$/,
  /^Paragem \d+: check-in em .+\.$/,
  /^A viagem registada chega à paragem \d+: .+\.$/,
];

const CHAPTER_TEMPLATES = {
  "zh-CN": {
    diary: "我来到了{name}。这是本次旅程的第{number}个打卡地点。",
    magazine: "第{number}站 · {name}。这一章节依据实际到访记录整理。",
    social: "第{number}站，打卡{name}。",
    documentary: "行程记录来到第{number}站：{name}。",
  },
  "zh-TW": {
    diary: "我來到了{name}。這是本次旅程的第{number}個打卡地點。",
    magazine: "第{number}站 · {name}。這一章節依據實際到訪記錄整理。",
    social: "第{number}站，打卡{name}。",
    documentary: "行程記錄來到第{number}站：{name}。",
  },
  en: {
    diary: "I arrived at {name}, the {number} stop recorded on this trip.",
    magazine: "Stop {number} · {name}. This chapter is assembled from the recorded visit.",
    social: "Stop {number}: checked in at {name}.",
    documentary: "The recorded journey reaches stop {number}: {name}.",
  },
  pt: {
    diary: "Cheguei a {name}, a {number}.ª paragem registada nesta viagem.",
    magazine: "Paragem {number} · {name}. Este capítulo baseia-se na visita registada.",
    social: "Paragem {number}: check-in em {name}.",
    documentary: "A viagem registada chega à paragem {number}: {name}.",
  },
} as const;

export function localizedMemoirTitle(title: string, language: LanguageCode) {
  return SYSTEM_TITLES.has(title) ? DEFAULT_TITLES[language] : title;
}

export function localizedMemoirIntroduction(value: string, language: LanguageCode) {
  return SYSTEM_INTRODUCTIONS.has(value) ? DEFAULT_INTRODUCTIONS[language] : value;
}

export function localizedMemoirClosing(value: string, language: LanguageCode) {
  return SYSTEM_CLOSINGS.has(value) ? DEFAULT_CLOSINGS[language] : value;
}

export function localizedMemoirChapterBody(
  value: string,
  style: keyof typeof CHAPTER_TEMPLATES["en"],
  number: number,
  name: string,
  language: LanguageCode,
) {
  if (!SYSTEM_CHAPTER_PATTERNS.some((pattern) => pattern.test(value))) return value;
  return CHAPTER_TEMPLATES[language][style]
    .replace("{number}", String(number))
    .replace("{name}", name);
}
