import fallbackHero from "@/assets/hero-ruins.jpg";

/** 行程常用景点 → 已下载到 public/poi 的固定图片。 */
const BY_POI_ID: Record<string, string> = {
  poi_0002: "/poi/poi_love_lane.jpg",
  poi_0007: "/poi/poi_fatong.jpg",
  poi_ama: "/poi/poi_ama.jpg",
  poi_mandarin_house: "/poi/poi_mandarin_house.jpg",
  poi_lilau: "/poi/poi_lilau.jpg",
  poi_dom_pedro_v: "/poi/poi_dom_pedro_v.jpg",
  poi_st_augustine: "/poi/poi_st_augustine.jpg",
  poi_senado: "/poi/poi_senado.jpg",
  poi_leal_senado: "/poi/poi_leal_senado.jpg",
  poi_st_dominic: "/poi/poi_st_dominic.jpg",
  poi_ruins_st_paul: "/poi/poi_ruins_st_paul.jpg",
  poi_na_tcha: "/poi/poi_na_tcha.jpg",
  poi_mount_fortress: "/poi/poi_mount_fortress.jpg",
  poi_holy_house_mercy: "/poi/poi_holy_house_mercy.jpg",
  poi_lou_kau: "/poi/poi_lou_kau.jpg",
  poi_fatong: "/poi/poi_fatong.jpg",
  poi_rua_cunha: "/poi/poi_rua_cunha.jpg",
  poi_taipa_houses: "/poi/poi_taipa_houses.jpg",
  poi_coloane_chapel: "/poi/poi_coloane_chapel.jpg",
};

const BY_NAME: Array<{ test: RegExp; url: string }> = [
  { test: /妈阁|媽閣|A-?\s*Ma|Templo de A-Má/i, url: BY_POI_ID.poi_ama },
  { test: /大三巴|聖保祿|圣保禄|St\.?\s*Paul|São Paulo/i, url: BY_POI_ID.poi_ruins_st_paul },
  { test: /议事亭|議事亭|Senado|Largo do Senado/i, url: BY_POI_ID.poi_senado },
  { test: /郑家大屋|鄭家大屋|Mandarin/i, url: BY_POI_ID.poi_mandarin_house },
  { test: /大炮台|炮兵|升降机|升降機|Mount\s*Fortress|Fortaleza do Monte|Monte Fort/i, url: BY_POI_ID.poi_mount_fortress },
  { test: /玫瑰堂|St\.?\s*Dominic|São Domingos/i, url: BY_POI_ID.poi_st_dominic },
  { test: /恋爱巷|戀愛巷|Paixão|paixao/i, url: BY_POI_ID.poi_0002 },
  { test: /东望洋|東望洋|Guia|灯塔|燈塔/i, url: BY_POI_ID.poi_fatong },
  { test: /官也街|官也|Rua da Cunha|Cunha/i, url: BY_POI_ID.poi_rua_cunha },
  { test: /龙环葡韵|龍環葡韻|Taipa Houses/i, url: BY_POI_ID.poi_taipa_houses },
];

const memoryCache = new Map<string, string>();

function imageIsAvailable(url: string): Promise<boolean> {
  return new Promise((resolve) => {
    const image = new Image();
    const timer = window.setTimeout(() => {
      image.src = "";
      resolve(false);
    }, 5000);
    image.onload = () => {
      window.clearTimeout(timer);
      resolve(true);
    };
    image.onerror = () => {
      window.clearTimeout(timer);
      resolve(false);
    };
    image.src = url;
  });
}

async function commonsSearchImage(query: string): Promise<string | null> {
  const params = new URLSearchParams({
    action: "query",
    format: "json",
    origin: "*",
    generator: "search",
    gsrnamespace: "6",
    gsrlimit: "6",
    gsrsearch: `${query} Macau filetype:bitmap`,
    prop: "imageinfo",
    iiprop: "url|mime",
    iiurlwidth: "1600",
  });
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(
      `https://commons.wikimedia.org/w/api.php?${params.toString()}`,
      { signal: controller.signal },
    );
    if (!response.ok) return null;
    const data = (await response.json()) as {
      query?: {
        pages?: Record<
          string,
          {
            imageinfo?: Array<{
              mime?: string;
              thumburl?: string;
              url?: string;
            }>;
          }
        >;
      };
    };
    const pages = Object.values(data.query?.pages ?? {});
    for (const page of pages) {
      const info = page.imageinfo?.[0];
      if (!info?.mime?.startsWith("image/")) continue;
      const url = info.thumburl || info.url;
      if (url && (await imageIsAvailable(url))) return url;
    }
  } catch {
    return null;
  } finally {
    window.clearTimeout(timer);
  }
  return null;
}

function enlargeWikiThumb(url: string): string {
  // .../thumb/.../40px-Foo.jpg → 1280px
  return url.replace(/\/(\d+)px-([^/]+)$/, "/1280px-$2");
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
    const commonsImage = await commonsSearchImage(title);
    if (commonsImage) {
      memoryCache.set(cacheKey, commonsImage);
      return commonsImage;
    }
    const wiki = await wikipediaImage(title);
    if (wiki && (await imageIsAvailable(wiki))) {
      memoryCache.set(cacheKey, wiki);
      return wiki;
    }
  }

  return fallbackHero;
}

export { fallbackHero };
