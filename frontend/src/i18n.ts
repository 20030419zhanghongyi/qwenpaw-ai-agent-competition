// 极简 i18n。Phase 2/3 接正式多语言生成 Agent 后再扩。
// 支持 zh-CN / zh-TW / en / pt，缺 key 回退到 zh-CN。

export type Lang = "zh-CN" | "zh-TW" | "en" | "pt";

export const LANG_OPTIONS: { code: Lang; label: string }[] = [
  { code: "zh-CN", label: "简体中文" },
  { code: "zh-TW", label: "繁體中文" },
  { code: "en", label: "English" },
  { code: "pt", label: "Português" },
];

type Dict = Record<string, string>;

const ZH: Dict = {
  appTitle: "澳跡同行 · Macau StoryWalk",
  chooseLang: "选择语言",
  start: "开始",
  preferences: "你的偏好",
  duration: "游览时长",
  "half-day": "半日游",
  "full-day": "一日游",
  evening: "夜间散步",
  interests: "兴趣偏好",
  travelType: "出行类型",
  physical: "体力偏好",
  lessWalk: "少走路",
  noBacktrack: "避免回头路",
  generate: "生成我的路线",
  matching: "正在为你配对路线…",
  routeResult: "推荐路线",
  reasons: "为什么推荐",
  nodes: "行程节点",
  back: "返回调整",
  error: "出错了，请确认后端已启动",
};

const DICTS: Record<Lang, Dict> = {
  "zh-CN": ZH,
  "zh-TW": {
    ...ZH,
    chooseLang: "選擇語言",
    start: "開始",
    preferences: "你的偏好",
    duration: "遊覽時長",
    "half-day": "半日遊",
    "full-day": "一日遊",
    evening: "夜間散步",
    interests: "興趣偏好",
    travelType: "出行類型",
    physical: "體力偏好",
    lessWalk: "少走路",
    noBacktrack: "避免回頭路",
    generate: "生成我的路線",
    matching: "正在為你配對路線…",
    routeResult: "推薦路線",
    reasons: "為什麼推薦",
    nodes: "行程節點",
    back: "返回調整",
  },
  en: {
    ...ZH,
    appTitle: "Macau StoryWalk",
    chooseLang: "Choose language",
    start: "Start",
    preferences: "Your preferences",
    duration: "Duration",
    "half-day": "Half day",
    "full-day": "Full day",
    evening: "Evening stroll",
    interests: "Interests",
    travelType: "Travel type",
    physical: "Physical level",
    lessWalk: "Less walking",
    noBacktrack: "No backtracking",
    generate: "Build my route",
    matching: "Matching routes…",
    routeResult: "Recommended route",
    reasons: "Why this route",
    nodes: "Itinerary",
    back: "Back",
  },
  pt: {
    ...ZH,
    appTitle: "Macau StoryWalk",
    chooseLang: "Escolher idioma",
    start: "Começar",
    preferences: "As suas preferências",
    duration: "Duração",
    "half-day": "Meio dia",
    "full-day": "Dia inteiro",
    evening: "Passeio noturno",
    interests: "Interesses",
    travelType: "Tipo de viagem",
    physical: "Esforço físico",
    lessWalk: "Caminhar menos",
    noBacktrack: "Sem voltar atrás",
    generate: "Gerar o meu percurso",
    matching: "A sugerir percursos…",
    routeResult: "Percurso recomendado",
    reasons: "Porquê este percurso",
    nodes: "Itinerário",
    back: "Voltar",
  },
};

export function t(lang: Lang, key: string): string {
  return DICTS[lang]?.[key] ?? ZH[key] ?? key;
}
