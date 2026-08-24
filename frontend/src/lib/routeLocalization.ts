import type { LanguageCode, RouteTemplate } from "@/types";

type LocalRoute = { name: string; theme: string; summary: string };

type ThemeCopy = {
  theme: string;
  dayName: string;
  summary: string;
};

const THEME_DAYS: Record<
  string,
  Partial<Record<LanguageCode, ThemeCopy>>
> = {
  heritage: {
    "zh-TW": { theme: "歷史城區", dayName: "歷史城區主題日", summary: "按歷史城區主題，從澳門文化景點池編排行程。" },
    en: { theme: "Historic centre", dayName: "Historic Centre Day", summary: "A personalized day built from Macau's historic-centre POIs." },
    pt: { theme: "Centro histórico", dayName: "Dia do Centro Histórico", summary: "Um dia personalizado criado a partir dos locais históricos de Macau." },
  },
  architecture: {
    "zh-TW": { theme: "建築漫遊", dayName: "建築漫遊主題日", summary: "按建築主題，從澳門文化景點池編排行程。" },
    en: { theme: "Architecture", dayName: "Architecture Day", summary: "A personalized day focused on Macau's architecture and streetscapes." },
    pt: { theme: "Arquitetura", dayName: "Dia de Arquitetura", summary: "Um dia personalizado dedicado à arquitetura e paisagem urbana de Macau." },
  },
  photo: {
    "zh-TW": { theme: "攝影打卡", dayName: "攝影打卡主題日", summary: "按攝影主題，從澳門文化景點池編排行程。" },
    en: { theme: "Photography", dayName: "Photography Day", summary: "A personalized day linking photogenic streets and landmarks." },
    pt: { theme: "Fotografia", dayName: "Dia de Fotografia", summary: "Um dia personalizado entre ruas e monumentos fotogénicos." },
  },
  food: {
    "zh-TW": { theme: "美食街巷", dayName: "美食街巷主題日", summary: "按美食街巷主題，從澳門景點池編排行程。" },
    en: { theme: "Food streets", dayName: "Food Streets Day", summary: "A personalized day exploring Macau's food streets and neighbourhood culture." },
    pt: { theme: "Ruas gastronómicas", dayName: "Dia das Ruas Gastronómicas", summary: "Um dia personalizado pelas ruas gastronómicas e bairros de Macau." },
  },
  family: {
    "zh-TW": { theme: "親子輕鬆", dayName: "親子輕鬆主題日", summary: "按親子與輕鬆步調，從澳門景點池編排行程。" },
    en: { theme: "Family", dayName: "Family Day", summary: "A relaxed personalized day suitable for families." },
    pt: { theme: "Família", dayName: "Dia em Família", summary: "Um dia personalizado e descontraído para famílias." },
  },
  leisure: {
    "zh-TW": { theme: "休閒漫步", dayName: "休閒漫步主題日", summary: "按休閒步調，從澳門景點池編排行程。" },
    en: { theme: "Leisure", dayName: "Leisure Day", summary: "A relaxed personalized day through Macau's neighbourhoods." },
    pt: { theme: "Lazer", dayName: "Dia de Lazer", summary: "Um dia personalizado e descontraído pelos bairros de Macau." },
  },
  cotai: {
    "zh-TW": { theme: "路氹景觀", dayName: "路氹景觀主題日", summary: "按路氹景觀主題，從澳門景點池編排行程。" },
    en: { theme: "Cotai", dayName: "Cotai Day", summary: "A personalized day exploring Cotai's public architecture and attractions." },
    pt: { theme: "Cotai", dayName: "Dia em Cotai", summary: "Um dia personalizado pela arquitetura pública e atrações de Cotai." },
  },
};

const GENERIC_ROUTE: Record<Exclude<LanguageCode, "zh-CN">, LocalRoute> = {
  "zh-TW": { name: "澳門個人化路線", theme: "文化漫遊", summary: "按你的偏好編排的澳門文化路線。" },
  en: { name: "Personalized Macau Route", theme: "Culture", summary: "A Macau cultural route arranged around your preferences." },
  pt: { name: "Rota Personalizada de Macau", theme: "Cultura", summary: "Uma rota cultural de Macau organizada segundo as suas preferências." },
};

const HAS_HAN = /[\u3400-\u9fff]/;

function themeKeys(route: RouteTemplate): string[] {
  const id = route.id.toLowerCase();
  const known = Object.keys(THEME_DAYS);
  if (id.startsWith("theme_day_mixed_")) {
    const suffix = id.slice("theme_day_mixed_".length);
    return known.filter((key) => suffix.split("_").includes(key));
  }
  const direct = known.find((key) => id.startsWith(`theme_day_${key}`));
  return direct ? [direct] : [];
}

function dynamicThemeRoute(route: RouteTemplate, language: LanguageCode): LocalRoute | null {
  if (language === "zh-CN" || !route.id.startsWith("theme_day_")) return null;
  const copies = themeKeys(route)
    .map((key) => THEME_DAYS[key]?.[language])
    .filter((copy): copy is ThemeCopy => Boolean(copy));
  if (copies.length === 0) return GENERIC_ROUTE[language];
  if (copies.length === 1) {
    return { name: copies[0].dayName, theme: copies[0].theme, summary: copies[0].summary };
  }
  const joiner = language === "pt" ? " e " : language === "en" ? " & " : " · ";
  const theme = copies.map((copy) => copy.theme).join(joiner);
  const name = language === "pt" ? `Dia de ${theme}` : language === "en" ? `${theme} Day` : `${theme}主題日`;
  const summary = language === "pt"
    ? `Um dia personalizado que combina ${theme}.`
    : language === "en"
      ? `A personalized day combining ${theme}.`
      : `結合${theme}偏好編排的澳門主題路線。`;
  return { name, theme, summary };
}

const ROUTES: Record<string, Partial<Record<LanguageCode, LocalRoute>>> = {
  heritage_fullday: {
    "zh-TW": { name: "歷史城區縱貫一日線", theme: "文化", summary: "由媽閣經議事亭前地前往大三巴及大炮台，串連澳門歷史城區的重要文化節點。" },
    en: { name: "Historic Centre Full-Day Route", theme: "Culture", summary: "Travel from A-Ma Temple through Senado Square to the Ruins of St. Paul's and Mount Fortress." },
    pt: { name: "Rota de Dia Inteiro pelo Centro Histórico", theme: "Cultura", summary: "Do Templo de A-Má pelo Largo do Senado até às Ruínas de São Paulo e à Fortaleza do Monte." },
  },
  culture_halfday: {
    "zh-TW": { name: "中區建築層次半日線", theme: "建築", summary: "由議事亭前地走向大炮台，觀察市政、宗教、民居及防禦建築。" },
    en: { name: "Central Macau Architecture Route", theme: "Architecture", summary: "A half-day architecture walk from Senado Square to Mount Fortress." },
    pt: { name: "Rota de Arquitetura do Centro", theme: "Arquitetura", summary: "Passeio de meio dia pelo património arquitetónico, do Largo do Senado à Fortaleza do Monte." },
  },
  photo_halfday: {
    "zh-TW": { name: "大三巴至望德堂攝影線", theme: "攝影", summary: "由戀愛巷經大三巴及大炮台走向望德堂區，適合觀察坡巷與城市層次。" },
    en: { name: "St. Paul's to St. Lazarus Photo Walk", theme: "Photography", summary: "A photo-focused walk through Travessa da Paixão, St. Paul's, Mount Fortress, and St. Lazarus." },
    pt: { name: "Passeio Fotográfico de São Paulo a São Lázaro", theme: "Fotografia", summary: "Percurso fotográfico pela Travessa da Paixão, São Paulo, Fortaleza do Monte e São Lázaro." },
  },
  food_family_halfday: {
    "zh-TW": { name: "中區至下環飲食文化線", theme: "美食", summary: "由議事亭前地經福隆新街前往下環街市，認識老街及社區飲食文化。" },
    en: { name: "Central Macau Food Culture Route", theme: "Food", summary: "Explore local food culture from Senado Square through Rua da Felicidade to S. Lourenço Market." },
    pt: { name: "Rota da Cultura Gastronómica do Centro", theme: "Gastronomia", summary: "Do Largo do Senado pela Rua da Felicidade até ao Mercado de S. Lourenço." },
  },
  taipa_hotspot_halfday: {
    "zh-TW": { name: "氹仔舊城親子觀察線", theme: "親子", summary: "串連官也街、嘉模聖母堂及龍環葡韻的短距離親子路線。" },
    en: { name: "Family Walk through Old Taipa", theme: "Family", summary: "A short family route linking Rua do Cunha, Our Lady of Carmel Church, and Taipa Houses." },
    pt: { name: "Passeio Familiar pela Taipa Antiga", theme: "Família", summary: "Rota curta pela Rua do Cunha, Igreja de Nossa Senhora do Carmo e Casas da Taipa." },
  },
  coloane_leisure_halfday: {
    "zh-TW": { name: "路環舊市區休閒線", theme: "休閒", summary: "由路環碼頭經恩尼斯總統前地前往聖方濟各聖堂。" },
    en: { name: "Old Coloane Leisure Walk", theme: "Leisure", summary: "A relaxed walk from Coloane Pier through the village square to St. Francis Xavier Chapel." },
    pt: { name: "Passeio de Lazer pela Vila de Coloane", theme: "Lazer", summary: "Do Cais de Coloane pela praça da vila até à Capela de São Francisco Xavier." },
  },
  cotai_theme_europe_halfday: {
    "zh-TW": { name: "路氹主題建築攝影半日線", theme: "攝影", summary: "以威尼斯人、巴黎人及倫敦人的公共建築與室內街景為主。" },
    en: { name: "Cotai Themed Architecture Photo Route", theme: "Photography", summary: "Explore the public architecture and indoor streetscapes of the Venetian, Parisian, and Londoner." },
    pt: { name: "Rota Fotográfica de Arquitetura Temática em Cotai", theme: "Fotografia", summary: "Explore a arquitetura pública e os espaços interiores do Venetian, Parisian e Londoner." },
  },
  cotai_resort_show_halfday: {
    "zh-TW": { name: "路氹綜合度假區景觀半日線", theme: "休閒", summary: "觀察新濠天地、永利皇宮及新濠影匯的公共建築與景觀。" },
    en: { name: "Cotai Resort Landscape Route", theme: "Leisure", summary: "See the public architecture and landscapes of City of Dreams, Wynn Palace, and Studio City." },
    pt: { name: "Rota Paisagística dos Resorts de Cotai", theme: "Lazer", summary: "Arquitetura e paisagem públicas de City of Dreams, Wynn Palace e Studio City." },
  },
  lotus_city_double_map: {
    "zh-TW": { name: "《蓮城雙圖：未盡之圖》劇情一日線", theme: "歷史劇情", summary: "沿六處真實地點閱讀兩張記錄不同真實的澳門地圖。" },
    en: { name: "Two Maps of the Lotus City Story Route", theme: "Historical story", summary: "Follow six real places to read two maps that record different truths about Macau." },
    pt: { name: "Rota Narrativa dos Dois Mapas da Cidade de Lótus", theme: "Narrativa histórica", summary: "Percorra seis locais reais para ler dois mapas que registam diferentes realidades de Macau." },
  },
  coloane_after_tide: {
    "zh-TW": { name: "《潮退之後》路環劇情半日線", theme: "海、手藝與社區", summary: "沿路環古廟、廣場、船廠及黑沙整理海、船、村、工、土的地方記憶。" },
    en: { name: "After the Tide: Coloane Story Route", theme: "Sea, craft, and community", summary: "Trace Coloane's temples, square, shipyards, and coast through five layers of local memory." },
    pt: { name: "Depois da Maré: Rota Narrativa de Coloane", theme: "Mar, ofícios e comunidade", summary: "Percorra templos, praça, estaleiros e costa de Coloane através de cinco camadas de memória local." },
  },
};

export function localizedRoute(route: RouteTemplate, language: LanguageCode): LocalRoute {
  if (language === "zh-CN") return { name: route.name, theme: route.theme, summary: route.description };
  const dynamic = dynamicThemeRoute(route, language);
  if (dynamic) return dynamic;
  const fixed = ROUTES[route.id]?.[language];
  if (fixed) return fixed;
  if (HAS_HAN.test(`${route.name} ${route.theme} ${route.description}`)) return GENERIC_ROUTE[language];
  return { name: route.name, theme: route.theme, summary: route.description };
}

export function localizedRouteReasons(
  route: RouteTemplate,
  reasons: string[],
  language: LanguageCode,
): string[] {
  if (language === "zh-CN") return reasons;

  const theme = localizedRoute(route, language).theme;
  const source = reasons.join(" ");
  const hours = Number(route.duration_hours || 0).toFixed(1);
  const copy = {
    "zh-TW": {
      theme: `按「${theme}」偏好編排`, pool: "從景點池生成，並非固定模板",
      hours: `已擴充至約 ${hours} 小時`, port: "已將入境口岸設為行程起點",
      transit: "長距離路段建議乘搭公共交通", weather: "出發前請查閱官方天氣提示",
      crowd: "活動與人流情況為估算值",
    },
    en: {
      theme: `Built around your ${theme.toLowerCase()} preference`, pool: "Generated from the POI pool, not a fixed template",
      hours: `Expanded to about ${hours} hours`, port: "Entry port fixed as the route starting point",
      transit: "Use public transport for long transfers", weather: "Check official weather alerts before departure",
      crowd: "Event and crowd conditions are estimates",
    },
    pt: {
      theme: `Criada segundo a preferência: ${theme}`, pool: "Gerada a partir do conjunto de POIs, não de um modelo fixo",
      hours: `Alargada para cerca de ${hours} horas`, port: "Porto de entrada definido como início da rota",
      transit: "Use transporte público nos trajetos longos", weather: "Consulte os avisos meteorológicos oficiais antes de partir",
      crowd: "As condições de eventos e multidões são estimativas",
    },
  }[language];

  const output = [copy.theme, copy.pool];
  if (/小時|小时|擴充|扩充/.test(source) || route.duration_hours >= 7) output.push(copy.hours);
  if (/口岸|入境|进境/.test(source)) output.push(copy.port);
  if (/巴士|公交|勿步行|穿梭/.test(source)) output.push(copy.transit);
  if (/天氣|天气/.test(source)) output.push(copy.weather);
  if (/活動|活动|人流|擁擠|拥挤/.test(source)) output.push(copy.crowd);
  return output;
}
