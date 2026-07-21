/**
 * Soft ethics helper: detect casino / gaming venues on a route day
 * so the UI can remind users not to gamble (see ethics/_ethics_base.md §9).
 *
 * Uses POI fields already available on the route result page (name, alias,
 * address, category). Avoids matching generic Amap "娱乐场所" (bars, etc.).
 */

export type GamblingPoiLike = {
  poi_name?: string | null;
  alias?: string | null;
  address?: string | null;
  category?: string | null;
};

/** Explicit gambling / casino floor signals in Macau POI text. */
const GAMBLING_KEYWORD_RE =
  /赌场|賭場|casino|gambling|博彩|赌厅|賭廳|投注站|马会投注|馬會投注|娛樂場(?!所)|娱乐场(?!所)/i;

/**
 * Integrated resorts / casino hotels common on peninsula & Cotai routes.
 * Name-based because Amap category is often just "五星级宾馆".
 */
const CASINO_RESORT_NAME_RE =
  /金沙酒店|葡京酒店|新葡京|上葡京|永利澳门|永利澳門|永利皇宫|永利皇宮|美高梅|威尼斯人|巴黎人|伦敦人|倫敦人|新濠天地|新濠影汇|新濠影匯|澳门银河|澳門銀河|银河酒店|銀河酒店|葡京人|\bmgm\b|\bwynn\b|venetian|parisian|londoner|\bsands\b|lisboa|city of dreams|studio city/i;

export function isGamblingRelatedPoi(
  poi: GamblingPoiLike | null | undefined,
): boolean {
  if (!poi) return false;
  const hay = [poi.poi_name, poi.alias, poi.address, poi.category]
    .filter((part): part is string => Boolean(part && part.trim()))
    .join(" ");
  if (!hay) return false;
  return GAMBLING_KEYWORD_RE.test(hay) || CASINO_RESORT_NAME_RE.test(hay);
}

/** True when any stop on the day looks like a casino / gaming venue. */
export function routeHasGamblingVenue(
  poiIds: readonly string[],
  poisById: Record<string, GamblingPoiLike>,
): boolean {
  return poiIds.some((id) => isGamblingRelatedPoi(poisById[id]));
}
