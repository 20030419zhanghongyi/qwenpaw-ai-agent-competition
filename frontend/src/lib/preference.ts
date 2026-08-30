import type { LanguageCode, Preference, StorySelection } from "@/types";

/** UI duration ids → backend Preference.duration */
const DURATION_MAP: Record<string, Preference["duration"]> = {
  half: "half-day",
  full: "full-day",
  night: "evening",
  multi: "multi-day",
};

const DURATION_FROM_API: Record<string, PreferenceFormState["duration"] | undefined> = {
  "half-day": "half",
  "full-day": "full",
  evening: "night",
  "multi-day": "multi",
  // custom = 未识别到时长，不要覆盖表单
  custom: undefined,
};

/** Walking UI tags that map directly to backend Preference.physical */
const PHYSICAL_BACKEND_TAGS = new Set(["less-walk", "no-backtrack"]);

/** Extra walking UI tags that imply less-walk for matching */
const PHYSICAL_SOFT_TAGS = new Set(["shade", "flat", "indoor", "accessible"]);

export type WalkTag =
  | "less-walk"
  | "no-backtrack"
  | "shade"
  | "flat"
  | "indoor"
  | "accessible";

export type ThemeTag =
  | "heritage"
  | "architecture"
  | "photo"
  | "food"
  | "family"
  | "leisure"
  | "cotai";

const THEME_TAGS = new Set<ThemeTag>([
  "heritage",
  "architecture",
  "photo",
  "food",
  "family",
  "leisure",
  "cotai",
]);

/** Multi-day day count (matches backend TRIP_DAYS_*) */
export const TRIP_DAYS_MIN = 2;
export const TRIP_DAYS_MAX = 5;
export const TRIP_DAYS_DEFAULT = 3;

export function clampTripDays(n: number): number {
  if (!Number.isFinite(n)) return TRIP_DAYS_DEFAULT;
  return Math.min(TRIP_DAYS_MAX, Math.max(TRIP_DAYS_MIN, Math.round(n)));
}

/** UI interest ids → backend interest tags */
const INTEREST_MAP: Record<string, string> = {
  history: "history",
  arch: "architecture",
  food: "food",
  photo: "photo",
  culture: "culture",
  relax: "relax",
};

const INTEREST_FROM_API: Record<string, string> = {
  history: "history",
  architecture: "arch",
  food: "food",
  photo: "photo",
  culture: "culture",
  relax: "relax",
};

export interface PreferenceFormState {
  duration: "half" | "full" | "night" | "multi";
  /** Days for multi-day plans; ignored unless duration === "multi" */
  tripDays: number;
  interests: string[];
  themes: ThemeTag[];
  companion: "solo" | "friends" | "family";
  walkTags: WalkTag[];
  customNote: string;
  language: LanguageCode;
  entryPort: string | null;
  exitPort: string | null;
  travelDate: string | null;
  storyOptIn: boolean | null;
  storyId: Preference["story_id"];
  storyDay: number | null;
  storySelections?: StorySelection[];
}

export function todayIso(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function toPreference(form: PreferenceFormState): Preference {
  const physical: string[] = [];
  for (const tag of form.walkTags) {
    if (PHYSICAL_BACKEND_TAGS.has(tag) && !physical.includes(tag)) {
      physical.push(tag);
    }
    if (PHYSICAL_SOFT_TAGS.has(tag) && !physical.includes("less-walk")) {
      physical.push("less-walk");
    }
  }
  if (physical.length === 0) physical.push("normal");

  const duration = DURATION_MAP[form.duration] ?? "half-day";
  const storySelections = form.storyOptIn
    ? (form.storySelections ?? []).filter((selection) => selection.story_day <= form.tripDays)
    : [];
  const primaryStory = storySelections[0] ?? (
    form.storyOptIn && form.storyId
      ? { story_id: form.storyId, story_day: form.storyDay ?? 1 }
      : null
  );
  return {
    duration,
    party_size: form.companion === "solo" ? 1 : form.companion === "friends" ? 2 : 3,
    travel_type: [form.companion],
    interests: form.interests.map((id) => INTEREST_MAP[id] ?? id),
    themes: [...form.themes],
    physical,
    language: form.language,
    entry_port: form.entryPort,
    exit_port: form.exitPort,
    travel_date: form.travelDate || todayIso(),
    trip_days: duration === "multi-day" ? clampTripDays(form.tripDays) : null,
    story_opt_in: form.storyOptIn,
    story_id: primaryStory?.story_id ?? null,
    story_day:
      primaryStory ? (duration === "multi-day" ? primaryStory.story_day : 1) : null,
    story_selections: storySelections,
  };
}

/** Apply intent/parse Preference onto the form (聊天/解析回填，增量合并)。 */
export function applyPreferenceToForm(
  pref: Preference,
  current: PreferenceFormState,
): PreferenceFormState {
  const walkTags = new Set<WalkTag>(current.walkTags);
  for (const tag of pref.physical ?? []) {
    if (tag === "less-walk" || tag === "no-backtrack") {
      walkTags.add(tag);
    }
  }

  const interests = new Set(current.interests);
  for (const tag of pref.interests ?? []) {
    const ui = INTEREST_FROM_API[tag];
    if (ui) interests.add(ui);
  }

  const themes = new Set<ThemeTag>(current.themes);
  for (const tag of pref.themes ?? []) {
    if (THEME_TAGS.has(tag as ThemeTag)) themes.add(tag as ThemeTag);
  }

  let companion = current.companion;
  let companionHit = false;
  for (const tag of pref.travel_type ?? []) {
    if (tag === "solo" || tag === "friends" || tag === "family") {
      companion = tag;
      companionHit = true;
      break;
    }
  }
  // Agent / soft parse 有时只给 party_size（忽略默认 1，避免误伤）
  if (!companionHit && typeof pref.party_size === "number") {
    if (pref.party_size >= 3) companion = "family";
    else if (pref.party_size === 2) companion = "friends";
  }

  const mappedDuration = DURATION_FROM_API[pref.duration];
  let tripDays = current.tripDays;
  if (typeof pref.trip_days === "number") {
    tripDays = clampTripDays(pref.trip_days);
  } else if (mappedDuration === "multi" && current.duration !== "multi") {
    tripDays = TRIP_DAYS_DEFAULT;
  }

  return {
    ...current,
    duration: mappedDuration ?? current.duration,
    tripDays,
    interests: [...interests],
    themes: [...themes],
    companion,
    walkTags: [...walkTags],
    language: (pref.language as LanguageCode) || current.language,
    entryPort: pref.entry_port ?? current.entryPort,
    exitPort: pref.exit_port ?? current.exitPort,
    travelDate: pref.travel_date ?? current.travelDate,
    storyOptIn: pref.story_opt_in ?? current.storyOptIn,
    storyId: pref.story_id ?? current.storyId,
    storyDay: pref.story_day ?? current.storyDay,
    storySelections: pref.story_selections?.length
      ? pref.story_selections
      : pref.story_id
        ? [{ story_id: pref.story_id, story_day: pref.story_day ?? 1 }]
        : current.storySelections ?? [],
  };
}

function inferTripDaysFromText(raw: string, t: string): number | null {
  const digit = t.match(/([2-5])\s*-?\s*(?:天|日|days?|dias?)/i);
  if (digit) return clampTripDays(Number(digit[1]));
  const wordPairs: Array<[RegExp, number]> = [
    [/两天|兩天|两日|兩日|两晚|兩晚|two\s*days|dois\s*dias/, 2],
    [/三天|三日|三晚|three\s*days|tr[eê]s\s*dias/, 3],
    [/四天|四日|four\s*days|quatro\s*dias/, 4],
    [/五天|五日|five\s*days|cinco\s*dias/, 5],
  ];
  for (const [re, days] of wordPairs) {
    if (re.test(t) || re.test(raw)) return days;
  }
  return null;
}

/** 从用户一句话即时推断 Preference（聊天→选项实时联动）。 */
export function inferPreferenceFromText(
  text: string,
  language: LanguageCode,
): Preference {
  const raw = text.trim();
  const t = raw.toLowerCase();
  const pref: Preference = {
    duration: "custom",
    party_size: 1,
    travel_type: [],
    interests: [],
    themes: [],
    physical: [],
    language,
  };

  const tripDays = inferTripDaysFromText(raw, t);
  if (tripDays != null) {
    pref.duration = "multi-day";
    pref.trip_days = tripDays;
  } else if (
    /多日|几天|幾天|两天|兩天|三天|住两|住兩|待几天|待幾天|玩几天|玩幾天|2\s*天|3\s*天|两晚|兩晚|三晚|multi[\s-]*day|several\s*days|a\s*few\s*days|long\s*weekend|v[aá]rios\s*dias|dois\s*dias/.test(
      t,
    ) ||
    raw.includes("多日游") ||
    raw.includes("多日遊")
  ) {
    pref.duration = "multi-day";
  } else if (
    /一整天|全天|一日|一天|一日游|一日遊|full\s*day|whole\s*day|all\s*day|dia\s*inteiro/.test(t)
  ) {
    pref.duration = "full-day";
  } else if (/晚上|夜间|夜間|夜游|夜遊|夜景|evening|\bnight\b|noturno|noite/.test(t)) {
    pref.duration = "evening";
  } else if (/半天|半日|半日游|半日遊|几小时|幾小時|下午|上午|half[\s-]*day|few\s*hours|meio\s*dia/.test(t)) {
    pref.duration = "half-day";
  }

  if (/家庭|亲子|親子|带老人|帶老人|带小孩|帶小孩|家人|family|kids|parents|família|familia/.test(t)) {
    pref.travel_type.push("family");
    pref.party_size = 3;
  } else if (/朋友|情侣|情侶|约会|約會|闺蜜|閨蜜|两个人|兩個人|friends|couple|amigos/.test(t)) {
    pref.travel_type.push("friends");
    pref.party_size = 2;
  } else if (/一个人|一個人|独自|獨自|自己|solo|alone|sozinho/.test(t)) {
    pref.travel_type.push("solo");
    pref.party_size = 1;
  }

  if (/历史|歷史|遗迹|遺跡|老街|古迹|古蹟|history|heritage|história|historia/.test(t)) {
    pref.interests.push("history");
  }
  if (/建筑|建築|教堂|牌坊|庙|廟|architecture|church|arquitetura/.test(t)) {
    pref.interests.push("architecture");
  }
  if (/美食|吃|小吃|葡挞|葡撻|food|snack|comida/.test(t)) {
    pref.interests.push("food");
  }
  if (/拍照|摄影|攝影|出片|打卡|photo|photograph|foto/.test(t)) {
    pref.interests.push("photo");
  }
  if (/文化|博物馆|博物館|展览|展覽|culture|museum|cultura/.test(t)) {
    pref.interests.push("culture");
  }
  if (/放松|放鬆|休闲|休閒|随便逛|隨便逛|relax|slow|calmo/.test(t)) {
    pref.interests.push("relax");
  }
  if (
    /路氹|金光大道|威尼斯人|巴黎人|伦敦人|倫敦人|度假村|赌场|賭場|cotai|casino|venetian|parisian|londoner/.test(
      t,
    )
  ) {
    pref.themes.push("cotai");
  }
  if (/历史城区|歷史城區|旧城|舊城|heritage|historic\s*centre/.test(t)) {
    pref.themes.push("heritage");
  }
  if (/亲子|親子|带小孩|帶小孩|family\s*theme/.test(t)) {
    pref.themes.push("family");
  }

  if (/少走|不想太累|走不动|轻松点|less\s*walk|not too tired|menos\s*andar/.test(t)) {
    pref.physical.push("less-walk");
  }
  if (/回头路|别绕路|顺路|no\s*backtrack|one\s*way|sem\s*voltar/.test(t)) {
    pref.physical.push("no-backtrack");
  }
  if (/少爬坡|台阶|陡坡|flat|hill|stairs|subidas/.test(t)) {
    if (!pref.physical.includes("less-walk")) pref.physical.push("less-walk");
  }
  if (/日晒|遮荫|shade|sombra/.test(t)) {
    if (!pref.physical.includes("less-walk")) pref.physical.push("less-walk");
  }
  if (/室内|空调|indoor/.test(t)) {
    if (!pref.physical.includes("less-walk")) pref.physical.push("less-walk");
  }

  const declinesStory = /不参加故事|不要故事|跳过故事|不想参加|no story|skip (?:the )?story|sem hist[oó]ria/.test(t);
  const wantsStory = /参加故事|故事线|故事路[线線]|想玩故事|愿意参加|願意參加|join (?:a |the )?story|story walk|participar.*hist[oó]ria/.test(t);
  if (declinesStory) pref.story_opt_in = false;
  else if (wantsStory) pref.story_opt_in = true;
  if (/莲城双图|蓮城雙圖|two maps|dois mapas/.test(t)) {
    pref.story_opt_in = true;
    pref.story_id = "lotus_city_double_map";
  } else if (/海风寄来的信|海風寄來的信|sea breeze|brisa do mar/.test(t)) {
    pref.story_opt_in = true;
    pref.story_id = "taipa_letters";
  } else if (/潮退之后|潮退之後|after the tide|depois da mar[eé]/.test(t)) {
    pref.story_opt_in = true;
    pref.story_id = "coloane_after_tide";
  }
  const storyDay = t.match(/第\s*([1-5])\s*[天日]|day\s*([1-5])|dia\s*([1-5])/i);
  if (storyDay) pref.story_day = Number(storyDay[1] || storyDay[2] || storyDay[3]);

  const portHits: string[] = [];
  if (/关闸|拱北|gongbei|portas\s*do\s*cerco/.test(t)) portHits.push("poi_port_guanja");
  if (/青茂|qingmao/.test(t)) portHits.push("poi_port_qingmao");
  if (/横琴|hengqin/.test(t)) portHits.push("poi_port_hengqin");
  if (/港珠澳|大桥口岸|hzmb/.test(t)) portHits.push("poi_port_hzmb");
  if (/外港|outer\s*harbour|outer\s*harbor/.test(t)) portHits.push("poi_port_outer_harbor");
  if (/内港|inner\s*harbour|inner\s*harbor|湾仔口岸/.test(t)) portHits.push("poi_0071");
  if (portHits.length === 1) {
    const only = portHits[0];
    if (/出|离|出境|leave|exit|sair/.test(t) && !/进|入|入境|entry|entrar/.test(t)) {
      pref.exit_port = only;
    } else {
      pref.entry_port = only;
    }
  } else if (portHits.length >= 2) {
    pref.entry_port = portHits[0];
    pref.exit_port = portHits[portHits.length - 1];
  }

  return pref;
}

/** 哪些 UI 字段因这次 Preference 发生了变化（用于高亮）。 */
export function changedFormKeys(
  before: PreferenceFormState,
  after: PreferenceFormState,
): string[] {
  const keys: string[] = [];
  if (before.duration !== after.duration) keys.push(`duration:${after.duration}`);
  if (before.tripDays !== after.tripDays) keys.push("tripDays");
  if (before.companion !== after.companion) keys.push(`companion:${after.companion}`);
  for (const id of after.interests) {
    if (!before.interests.includes(id)) keys.push(`interest:${id}`);
  }
  for (const id of after.themes) {
    if (!before.themes.includes(id)) keys.push(`theme:${id}`);
  }
  for (const id of after.walkTags) {
    if (!before.walkTags.includes(id)) keys.push(`walk:${id}`);
  }
  if (before.entryPort !== after.entryPort && after.entryPort) {
    keys.push(`entryPort:${after.entryPort}`);
  }
  if (before.exitPort !== after.exitPort && after.exitPort) {
    keys.push(`exitPort:${after.exitPort}`);
  }
  if (before.storyOptIn !== after.storyOptIn) keys.push("storyOptIn");
  if (before.storyId !== after.storyId && after.storyId) keys.push(`story:${after.storyId}`);
  if (before.storyDay !== after.storyDay && after.storyDay) keys.push("storyDay");
  return keys;
}

export function durationLabelKey(
  duration: PreferenceFormState["duration"],
): "durationHalfShort" | "durationFullShort" | "durationNightShort" | "durationMultiShort" {
  if (duration === "full") return "durationFullShort";
  if (duration === "night") return "durationNightShort";
  if (duration === "multi") return "durationMultiShort";
  return "durationHalfShort";
}

export function physicalLevelLabel(
  level: string,
  labels: { low: string; med: string; high: string },
): string {
  if (level === "low") return labels.low;
  if (level === "high") return labels.high;
  return labels.med;
}

export function formatWalkMeta(opts: {
  stops: number;
  walkKm: number;
  durationHours: number;
  physicalLevel: string;
  stopsLabel: string;
  about: string;
  physical: { low: string; med: string; high: string };
}): string[] {
  const hours = opts.durationHours;
  const durationText =
    hours < 1
      ? `${opts.about} ${Math.round(hours * 60)}m`
      : hours % 1 === 0
        ? `${opts.about} ${hours}h`
        : `${opts.about} ${Math.floor(hours)}h ${Math.round((hours % 1) * 60)}m`;

  return [
    `${opts.stops} ${opts.stopsLabel}`,
    `${opts.walkKm.toFixed(1)} km`,
    durationText,
    physicalLevelLabel(opts.physicalLevel, opts.physical),
  ];
}
