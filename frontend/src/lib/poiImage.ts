import fallbackHero from "@/assets/hero-ruins.jpg";

/** Wikimedia Commons 直链（Special:FilePath 会 302 到真实文件）。 */
function commons(file: string, width = 1600): string {
  return `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(file)}?width=${width}`;
}

/** 行程常用景点 → Commons 文件名（可逐步补全）。 */
const BY_POI_ID: Record<string, string> = {
  poi_ama: commons("A-Ma Temple Macau 2013.jpg"),
  poi_mandarin_house: commons("Mandarin's House Macau.jpg"),
  poi_lilau: commons("Lilau Square Macau.jpg"),
  poi_st_lawrence: commons("Igreja de São Lourenço (Macau).jpg"),
  poi_st_joseph: commons("St. Joseph's Seminary and Church Macau.jpg"),
  poi_dom_pedro_v: commons("Dom Pedro V Theatre Macau.jpg"),
  poi_st_augustine: commons("St. Augustine's Church Macau.jpg"),
  poi_senado: commons("Largo do Senado Macau 2019.jpg"),
  poi_leal_senado: commons("Leal Senado Building Macau.jpg"),
  poi_st_dominic: commons("St. Dominic's Church Macau.jpg"),
  poi_ruins_st_paul: commons("The Ruins of St. Paul's in Macau.jpg"),
  poi_na_tcha: commons("Na Tcha Temple Macau.jpg"),
  poi_mount_fortress: commons("Fortaleza do Monte Macau.jpg"),
  poi_holy_house_mercy: commons("Holy House of Mercy Macau.jpg"),
  poi_cathedral: commons("Cathedral of the Nativity of Our Lady Macau.jpg"),
  poi_lou_kau: commons("Lou Kau Mansion Macau.jpg"),
  poi_fatong: commons("Guia Fortress Macau.jpg"),
  poi_moorish_barracks: commons("Moorish Barracks Macau.jpg"),
  poi_rua_cunha: commons("Rua da Cunha Taipa Macau.jpg"),
  poi_taipa_houses: commons("Taipa Houses-Museum.jpg"),
  poi_coloane_chapel: commons("Chapel of St. Francis Xavier Coloane.jpg"),
};

const BY_NAME: Array<{ test: RegExp; url: string }> = [
  { test: /妈阁|媽閣|A-?\s*Ma|Templo de A-Má/i, url: BY_POI_ID.poi_ama },
  { test: /大三巴|聖保祿|圣保禄|St\.?\s*Paul|São Paulo/i, url: BY_POI_ID.poi_ruins_st_paul },
  { test: /议事亭|議事亭|Senado|Largo do Senado/i, url: BY_POI_ID.poi_senado },
  { test: /郑家大屋|鄭家大屋|Mandarin/i, url: BY_POI_ID.poi_mandarin_house },
  { test: /大炮台|炮兵|升降机|升降機|Mount\s*Fortress|Fortaleza do Monte|Monte Fort/i, url: BY_POI_ID.poi_mount_fortress },
  { test: /玫瑰堂|St\.?\s*Dominic|São Domingos/i, url: BY_POI_ID.poi_st_dominic },
  { test: /恋爱巷|戀愛巷|Paixão|paixao/i, url: BY_POI_ID.poi_ruins_st_paul },
  { test: /东望洋|東望洋|Guia|灯塔|燈塔/i, url: BY_POI_ID.poi_fatong },
  { test: /官也街|官也|Rua da Cunha|Cunha/i, url: BY_POI_ID.poi_rua_cunha },
  { test: /龙环葡韵|龍環葡韻|Taipa Houses/i, url: BY_POI_ID.poi_taipa_houses },
];

const memoryCache = new Map<string, string>();

function enlargeWikiThumb(url: string): string {
  // .../thumb/.../40px-Foo.jpg → 1280px
  return url.replace(/\/(\d+)px-([^/]+)$/, "/1280px-$2");
}

function staticMapUrl(lat: number, lng: number): string | null {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  if (lat === 0 && lng === 0) return null;
  return `https://staticmap.openstreetmap.de/staticmap.php?center=${lat},${lng}&zoom=17&size=960x720&maptype=mapnik&markers=${lat},${lng},red-pushpin`;
}

async function wikipediaImage(title: string): Promise<string | null> {
  const langs = ["zh", "en"];
  for (const lang of langs) {
    try {
      const res = await fetch(
        `https://${lang}.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`,
        { headers: { Accept: "application/json" } },
      );
      if (!res.ok) continue;
      const data = (await res.json()) as {
        type?: string;
        originalimage?: { source?: string };
        thumbnail?: { source?: string };
      };
      if (data.type === "disambiguation") continue;
      const src = data.originalimage?.source || data.thumbnail?.source;
      if (src) return enlargeWikiThumb(src);
    } catch {
      // try next
    }
  }
  return null;
}

export function curatedPoiImage(poiId?: string | null, name?: string | null): string | null {
  if (poiId && BY_POI_ID[poiId]) return BY_POI_ID[poiId];
  if (name) {
    for (const row of BY_NAME) {
      if (row.test.test(name)) return row.url;
    }
  }
  return null;
}

/** 解析景点展示图：用户图 > 精选/维基 > 定位图 > 默认氛围图。 */
export async function resolvePoiImage(args: {
  poiId?: string | null;
  name?: string | null;
  alias?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  userPhotoUrl?: string | null;
}): Promise<string> {
  if (args.userPhotoUrl) return args.userPhotoUrl;

  const cacheKey = args.poiId || args.name || "";
  if (cacheKey && memoryCache.has(cacheKey)) {
    return memoryCache.get(cacheKey)!;
  }

  const curated = curatedPoiImage(args.poiId, args.name);
  if (curated) {
    memoryCache.set(cacheKey, curated);
    return curated;
  }

  const titles = [args.name, args.alias].filter(Boolean) as string[];
  for (const title of titles) {
    const wiki = await wikipediaImage(title);
    if (wiki) {
      memoryCache.set(cacheKey, wiki);
      return wiki;
    }
  }

  const map = staticMapUrl(args.latitude ?? NaN, args.longitude ?? NaN);
  if (map) {
    memoryCache.set(cacheKey, map);
    return map;
  }

  return fallbackHero;
}

export { fallbackHero };
