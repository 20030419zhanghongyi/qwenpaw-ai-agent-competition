import type { LanguageCode, Preference } from "@/types";

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

export interface PreferenceFormState {
  duration: "half" | "full" | "night" | "multi";
  interests: string[];
  themes: ThemeTag[];
  companion: "solo" | "friends" | "family";
  walkTags: WalkTag[];
  customNote: string;
  language: LanguageCode;
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

  return {
    duration: DURATION_MAP[form.duration] ?? "half-day",
    party_size: form.companion === "solo" ? 1 : form.companion === "friends" ? 2 : 3,
    travel_type: [form.companion],
    interests: form.interests.map((id) => INTEREST_MAP[id] ?? id),
    themes: [...form.themes],
    physical,
    language: form.language,
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

  return {
    ...current,
    duration: mappedDuration ?? current.duration,
    interests: [...interests],
    themes: [...themes],
    companion,
    walkTags: [...walkTags],
    language: (pref.language as LanguageCode) || current.language,
  };
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

  if (
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

  return pref;
}

/** 哪些 UI 字段因这次 Preference 发生了变化（用于高亮）。 */
export function changedFormKeys(
  before: PreferenceFormState,
  after: PreferenceFormState,
): string[] {
  const keys: string[] = [];
  if (before.duration !== after.duration) keys.push(`duration:${after.duration}`);
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
