import type { LanguageCode, POI } from "@/types";
import generatedPoiNames from "@/data/poiNames.generated.json";

type PoiNames = Record<LanguageCode, string>;
type PartialPoiNames = Partial<PoiNames>;

const GENERATED_NAMES = generatedPoiNames.names as Record<string, PartialPoiNames>;

const NAMES: Record<string, PoiNames> = {
  poi_port_guanja: { "zh-CN": "关闸口岸", "zh-TW": "關閘口岸", en: "Portas do Cerco Border Gate", pt: "Posto Fronteiriço das Portas do Cerco" },
  poi_port_qingmao: { "zh-CN": "青茂口岸", "zh-TW": "青茂口岸", en: "Qingmao Port", pt: "Posto Fronteiriço Qingmao" },
  poi_port_hengqin: { "zh-CN": "横琴口岸", "zh-TW": "橫琴口岸", en: "Hengqin Port", pt: "Posto Fronteiriço de Hengqin" },
  poi_port_hzmb: { "zh-CN": "港珠澳大桥澳门口岸", "zh-TW": "港珠澳大橋澳門口岸", en: "Hong Kong-Zhuhai-Macao Bridge Macao Port", pt: "Posto Fronteiriço da Ponte Hong Kong-Zhuhai-Macau" },
  poi_port_outer_harbor: { "zh-CN": "外港客运码头", "zh-TW": "外港客運碼頭", en: "Outer Harbour Ferry Terminal", pt: "Terminal Marítimo do Porto Exterior" },
  poi_0001: { "zh-CN": "大三巴牌坊", "zh-TW": "大三巴牌坊", en: "Ruins of St. Paul's", pt: "Ruínas de São Paulo" },
  poi_0002: { "zh-CN": "恋爱巷", "zh-TW": "戀愛巷", en: "Travessa da Paixão", pt: "Travessa da Paixão" },
  poi_0003: { "zh-CN": "澳门博物馆", "zh-TW": "澳門博物館", en: "Macao Museum", pt: "Museu de Macau" },
  poi_0004: { "zh-CN": "议事亭前地", "zh-TW": "議事亭前地", en: "Senado Square", pt: "Largo do Senado" },
  poi_0005: { "zh-CN": "玫瑰圣母堂", "zh-TW": "玫瑰聖母堂", en: "St. Dominic's Church", pt: "Igreja de São Domingos" },
  poi_0006: { "zh-CN": "塔石广场", "zh-TW": "塔石廣場", en: "Tap Seac Square", pt: "Praça do Tap Seac" },
  poi_0007: { "zh-CN": "东望洋灯塔", "zh-TW": "東望洋燈塔", en: "Guia Lighthouse", pt: "Farol da Guia" },
  poi_0008: { "zh-CN": "官也街", "zh-TW": "官也街", en: "Rua do Cunha", pt: "Rua do Cunha" },
  poi_0009: { "zh-CN": "玫瑰堂", "zh-TW": "玫瑰堂", en: "St. Dominic's Church", pt: "Igreja de São Domingos" },
  poi_0010: { "zh-CN": "大炮台升降机", "zh-TW": "大炮台升降機", en: "Mount Fortress Lift", pt: "Elevador da Fortaleza do Monte" },
  poi_0011: { "zh-CN": "妈阁庙", "zh-TW": "媽閣廟", en: "A-Ma Temple", pt: "Templo de A-Má" },
  poi_0012: { "zh-CN": "龙环葡韵住宅式博物馆", "zh-TW": "龍環葡韻住宅式博物館", en: "Taipa Houses", pt: "Casas da Taipa" },
  poi_0013: { "zh-CN": "Wood House", "zh-TW": "Wood House", en: "Wood House", pt: "Wood House" },
  poi_0014: { "zh-CN": "圣道明会院", "zh-TW": "聖道明會院", en: "St. Dominic's Priory and Chapel", pt: "Convento e Capela de São Domingos" },
  poi_0015: { "zh-CN": "郑家大屋", "zh-TW": "鄭家大屋", en: "Mandarin's House", pt: "Casa do Mandarim" },
  poi_0016: { "zh-CN": "福隆新街", "zh-TW": "福隆新街", en: "Rua da Felicidade", pt: "Rua da Felicidade" },
  poi_0017: { "zh-CN": "亚婆井前地", "zh-TW": "亞婆井前地", en: "Lilau Square", pt: "Largo do Lilau" },
  poi_0018: { "zh-CN": "疯堂斜巷", "zh-TW": "瘋堂斜巷", en: "St. Lazarus Quarter", pt: "Bairro de São Lázaro" },
  poi_0019: { "zh-CN": "氹仔旧城区艺术空间", "zh-TW": "氹仔舊城區藝術空間", en: "Taipa Village Art Space", pt: "Espaço de Arte da Vila da Taipa" },
  poi_0020: { "zh-CN": "澳门威尼斯人", "zh-TW": "澳門威尼斯人", en: "The Venetian Macao", pt: "The Venetian Macao" },
  poi_0021: { "zh-CN": "澳门巴黎人", "zh-TW": "澳門巴黎人", en: "The Parisian Macao", pt: "The Parisian Macao" },
  poi_0022: { "zh-CN": "澳门旅游塔", "zh-TW": "澳門旅遊塔", en: "Macau Tower", pt: "Torre de Macau" },
  poi_0023: { "zh-CN": "路环市区／卫生站", "zh-TW": "路環市區／衛生站", en: "Coloane Village Health Centre", pt: "Centro de Saúde da Vila de Coloane" },
  poi_0024: { "zh-CN": "黑沙海滩", "zh-TW": "黑沙海灘", en: "Hac Sa Beach", pt: "Praia de Hac Sá" },
  poi_0025: { "zh-CN": "澳门渔人码头", "zh-TW": "澳門漁人碼頭", en: "Macau Fisherman's Wharf", pt: "Doca dos Pescadores de Macau" },
  poi_0026: { "zh-CN": "南湾湖", "zh-TW": "南灣湖", en: "Nam Van Lake", pt: "Lago Nam Van" },
  poi_0027: { "zh-CN": "永利皇宫", "zh-TW": "永利皇宮", en: "Wynn Palace", pt: "Wynn Palace" },
  poi_0028: { "zh-CN": "澳门文化中心", "zh-TW": "澳門文化中心", en: "Macao Cultural Centre", pt: "Centro Cultural de Macau" },
  poi_0029: { "zh-CN": "关前正街", "zh-TW": "關前正街", en: "Rua dos Ervanários", pt: "Rua dos Ervanários" },
  poi_0030: { "zh-CN": "疯堂斜巷", "zh-TW": "瘋堂斜巷", en: "St. Lazarus Quarter", pt: "Bairro de São Lázaro" },
  poi_0031: { "zh-CN": "三盏灯圆形地", "zh-TW": "三盞燈圓形地", en: "Rotunda de Carlos da Maia", pt: "Rotunda de Carlos da Maia" },
  poi_0034: { "zh-CN": "东望洋新街", "zh-TW": "東望洋新街", en: "Rua Nova à Guia", pt: "Rua Nova à Guia" },
  poi_0048: { "zh-CN": "杏香园甜品", "zh-TW": "杏香園甜品", en: "Hang Heong Un Dessert", pt: "Hang Heong Un Dessert" },
  poi_0049: { "zh-CN": "哪咤古庙", "zh-TW": "哪吒古廟", en: "Na Tcha Temple", pt: "Templo de Na Tcha" },
  poi_0050: { "zh-CN": "圣老楞佐教堂", "zh-TW": "聖老楞佐教堂", en: "St. Lawrence's Church", pt: "Igreja de S. Lourenço" },
  poi_0051: { "zh-CN": "岗顶剧院", "zh-TW": "崗頂劇院", en: "Dom Pedro V Theatre", pt: "Teatro D. Pedro V" },
  poi_0052: { "zh-CN": "圣若瑟修院及圣堂", "zh-TW": "聖若瑟修院及聖堂", en: "St. Joseph's Seminary and Church", pt: "Seminário e Igreja de S. José" },
  poi_0053: { "zh-CN": "圣奥斯定教堂", "zh-TW": "聖奧斯定教堂", en: "St. Augustine's Church", pt: "Igreja de Santo Agostinho" },
  poi_0054: { "zh-CN": "澳门主教座堂", "zh-TW": "澳門主教座堂", en: "Cathedral", pt: "Igreja da Sé Catedral" },
  poi_0055: { "zh-CN": "仁慈堂大楼", "zh-TW": "仁慈堂大樓", en: "Holy House of Mercy", pt: "Santa Casa da Misericórdia de Macau" },
  poi_0056: { "zh-CN": "市政署大楼", "zh-TW": "市政署大樓", en: "Leal Senado Building", pt: "Edifício do Leal Senado" },
  poi_0057: { "zh-CN": "卢家大屋", "zh-TW": "盧家大屋", en: "Lou Kau Mansion", pt: "Casa de Lou Kau" },
  poi_0059: { "zh-CN": "东望洋炮台", "zh-TW": "東望洋炮台", en: "Guia Fortress", pt: "Fortaleza da Guia" },
  poi_0060: { "zh-CN": "澳门科学馆", "zh-TW": "澳門科學館", en: "Macao Science Center", pt: "Centro de Ciência de Macau" },
  poi_0071: { "zh-CN": "内港客运码头", "zh-TW": "內港客運碼頭", en: "Inner Harbour Ferry Terminal", pt: "Terminal Marítimo do Porto Interior" },
  poi_0115: { "zh-CN": "澳门大赛车博物馆", "zh-TW": "澳門大賽車博物館", en: "Macao Grand Prix Museum", pt: "Museu do Grande Prémio de Macau" },
  poi_0118: { "zh-CN": "益隆炮竹厂旧址", "zh-TW": "益隆炮竹廠舊址", en: "Former Iec Long Firecracker Factory", pt: "Antiga Fábrica de Panchões Iec Long" },
  poi_0126: { "zh-CN": "天主教圣安多尼堂", "zh-TW": "天主教聖安多尼堂", en: "St. Anthony's Church", pt: "Igreja de Santo António" },
  poi_0127: { "zh-CN": "圣母雪地殿教堂", "zh-TW": "聖母雪地殿教堂", en: "Chapel of Our Lady of the Snows", pt: "Capela de Nossa Senhora das Neves" },
  poi_0128: { "zh-CN": "岗顶前地", "zh-TW": "崗頂前地", en: "St. Augustine's Square", pt: "Largo de Santo Agostinho" },
  poi_0129: { "zh-CN": "何东图书馆大楼", "zh-TW": "何東圖書館大樓", en: "Sir Robert Ho Tung Library Building", pt: "Edifício da Biblioteca Sir Robert Ho Tung" },
  poi_0132: { "zh-CN": "基督教坟场", "zh-TW": "基督教墳場", en: "Protestant Cemetery", pt: "Cemitério Protestante" },
  poi_0133: { "zh-CN": "旧城墙遗址", "zh-TW": "舊城牆遺址", en: "Old City Walls", pt: "Antigas Muralhas da Cidade" },
  poi_0134: { "zh-CN": "大堂前地", "zh-TW": "大堂前地", en: "Cathedral Square", pt: "Largo da Sé" },
  poi_0135: { "zh-CN": "板樟堂前地", "zh-TW": "板樟堂前地", en: "St. Dominic's Square", pt: "Largo de S. Domingos" },
  poi_0136: { "zh-CN": "三街会馆", "zh-TW": "三街會館", en: "Sam Kai Vui Kun (Kuan Tai Temple)", pt: "Sam Kai Vui Kun (Templo de Kuan Tai)" },
  poi_0145: { "zh-CN": "澳门林则徐纪念馆", "zh-TW": "澳門林則徐紀念館", en: "Lin Zexu Memorial Museum of Macao", pt: "Museu Memorial Lin Zexu de Macau" },
  poi_0146: { "zh-CN": "典当业展示馆", "zh-TW": "典當業展示館", en: "Heritage Exhibition of a Traditional Pawnshop Business", pt: "Espaço Patrimonial - Uma Casa de Penhores Tradicional" },
  poi_0148: { "zh-CN": "海事博物馆", "zh-TW": "海事博物館", en: "Maritime Museum", pt: "Museu Marítimo" },
  poi_0149: { "zh-CN": "澳门消防局博物馆", "zh-TW": "澳門消防局博物館", en: "Fire Services Museum", pt: "Museu dos Bombeiros" },
  poi_0150: { "zh-CN": "通讯博物馆", "zh-TW": "通訊博物館", en: "Communications Museum", pt: "Museu das Comunicações" },
  poi_0230: { "zh-CN": "永利皇宫缆车站", "zh-TW": "永利皇宮纜車站", en: "Wynn Palace SkyCab Station", pt: "Estação do SkyCab do Wynn Palace" },
  poi_0231: { "zh-CN": "永利皇宫表演湖", "zh-TW": "永利皇宮表演湖", en: "Wynn Palace Performance Lake", pt: "Lago de Espetáculos do Wynn Palace" },
  poi_0236: { "zh-CN": "天后古庙", "zh-TW": "天后古廟", en: "Tin Hau Temple", pt: "Templo de Tin Hau" },
  poi_0240: { "zh-CN": "谭公庙", "zh-TW": "譚公廟", en: "Tam Kung Temple", pt: "Templo de Tam Kung" },
  poi_0241: { "zh-CN": "圣方济各圣堂及广场", "zh-TW": "聖方濟各聖堂及廣場", en: "Chapel of St. Francis Xavier and Square", pt: "Capela de São Francisco Xavier e Largo" },
  poi_0330: { "zh-CN": "荔枝碗船厂片区", "zh-TW": "荔枝碗船廠片區", en: "Lai Chi Vun Shipyards", pt: "Estaleiros de Lai Chi Vun" },
};

const LEGACY_IDS: Record<string, string> = {
  poi_ama: "poi_0011", poi_carmo: "poi_0098", poi_cathedral: "poi_0054",
  poi_coloane_chapel: "poi_0234", poi_coloane_pier: "poi_0238",
  poi_dom_pedro_v: "poi_0051", poi_eanes_square: "poi_0241", poi_fatong: "poi_0018",
  poi_florindo: "poi_0016", poi_holy_house_mercy: "poi_0055",
  poi_ho_tung_library: "poi_0129", poi_leal_senado: "poi_0056", poi_lilau: "poi_0017",
  poi_lou_kau: "poi_0057", poi_mandarin_house: "poi_0015",
  poi_moorish_barracks: "poi_0170", poi_mount_fortress: "poi_0003",
  poi_na_tcha: "poi_0049", poi_old_city_walls: "poi_0133", poi_paixao: "poi_0002",
  poi_rua_cunha: "poi_0008", poi_ruins_st_paul: "poi_0001", poi_senado: "poi_0004",
  poi_st_augustine: "poi_0053", poi_st_dominic: "poi_0009", poi_st_joseph: "poi_0052",
  poi_st_lawrence: "poi_0050", poi_sv_lazaro: "poi_0030",
  poi_taipa_houses: "poi_0012", poi_xiahuan: "poi_0168",
};

const META_FALLBACK: Record<LanguageCode, string> = {
  "zh-CN": "澳门地点",
  "zh-TW": "澳門地點",
  en: "Macau place",
  pt: "Local de Macau",
};

const BORDER_CROSSING_LABEL: Record<LanguageCode, string> = {
  "zh-CN": "出入境口岸",
  "zh-TW": "出入境口岸",
  en: "Border crossing",
  pt: "Posto fronteiriço",
};

const FERRY_TERMINAL_LABEL: Record<LanguageCode, string> = {
  "zh-CN": "客运码头",
  "zh-TW": "客運碼頭",
  en: "Ferry terminal",
  pt: "Terminal marítimo",
};

const CATEGORY_LABELS: Array<[RegExp, Record<LanguageCode, string>]> = [
  [/博物馆|博物館/, { "zh-CN": "博物馆", "zh-TW": "博物館", en: "Museum", pt: "Museu" }],
  [/教堂/, { "zh-CN": "教堂", "zh-TW": "教堂", en: "Church", pt: "Igreja" }],
  [/寺庙|寺廟|道观|道觀/, { "zh-CN": "寺庙", "zh-TW": "寺廟", en: "Temple", pt: "Templo" }],
  [/海滩|海灘/, { "zh-CN": "海滩", "zh-TW": "海灘", en: "Beach", pt: "Praia" }],
  [/公交车站|公交車站/, { "zh-CN": "公交站", "zh-TW": "巴士站", en: "Bus stop", pt: "Paragem de autocarro" }],
  [/餐饮|餐飲|中餐厅|中餐廳|快餐厅|快餐廳|咖啡厅|咖啡廳|糕饼店|糕餅店|甜品店/, { "zh-CN": "餐饮店", "zh-TW": "餐飲店", en: "Restaurant", pt: "Restaurante" }],
  [/购物|購物|商场|商場|专卖店|專賣店/, { "zh-CN": "商店", "zh-TW": "商店", en: "Shop", pt: "Loja" }],
  [/酒店|宾馆|賓館/, { "zh-CN": "酒店", "zh-TW": "酒店", en: "Hotel", pt: "Hotel" }],
  [/图书馆|圖書館/, { "zh-CN": "图书馆", "zh-TW": "圖書館", en: "Library", pt: "Biblioteca" }],
  [/市场|市場|街市/, { "zh-CN": "街市", "zh-TW": "街市", en: "Market", pt: "Mercado" }],
  [/体育馆|體育館|运动场馆|運動場館|游泳馆|游泳館/, { "zh-CN": "体育场馆", "zh-TW": "體育場館", en: "Sports venue", pt: "Instalação desportiva" }],
  [/剧场|劇場|影剧院|影劇院|电影院|電影院|展览馆|展覽館|会展中心|會展中心/, { "zh-CN": "文化场馆", "zh-TW": "文化場館", en: "Cultural venue", pt: "Espaço cultural" }],
  [/公园|公園/, { "zh-CN": "公园", "zh-TW": "公園", en: "Park", pt: "Parque" }],
  [/湖泊|水库|水庫/, { "zh-CN": "湖泊", "zh-TW": "湖泊", en: "Lake", pt: "Lago" }],
  [/道路名|街/, { "zh-CN": "特色街区", "zh-TW": "特色街區", en: "Historic street", pt: "Rua histórica" }],
  [/广场|廣場/, { "zh-CN": "广场", "zh-TW": "廣場", en: "Square", pt: "Praça" }],
  [/风景名胜|風景名勝|旅游景点|旅遊景點/, { "zh-CN": "文化景点", "zh-TW": "文化景點", en: "Cultural landmark", pt: "Marco cultural" }],
];

function canonicalId(poiId: string) {
  return LEGACY_IDS[poiId] ?? poiId;
}

function hasHan(text: string) {
  return /[\u3400-\u9fff]/.test(text);
}

function latinLabel(text: string) {
  const candidate = text
    .replace(/[\u3400-\u9fff]/g, " ")
    .replace(/[（）()[\]]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return (candidate.match(/[A-Za-zÀ-ž]/g) || []).length >= 4 ? candidate : "";
}

export function toTraditionalText(value: string): string {
  const characters: Record<string, string> = {
    澳: "澳", 门: "門", 恋: "戀", 爱: "愛", 议: "議", 场: "場", 馆: "館",
    圣: "聖", 东: "東", 灯: "燈", 妈: "媽", 阁: "閣", 龙: "龍", 环: "環",
    韵: "韻", 旧: "舊", 艺: "藝", 术: "術", 旅: "旅", 游: "遊", 渔: "漁",
    码: "碼", 头: "頭", 湾: "灣", 关: "關", 盏: "盞", 书: "書", 楼: "樓",
    墙: "牆", 遗: "遺", 会: "會", 纪: "紀", 念: "念", 当: "當", 业: "業",
    厂: "廠", 坟: "墳", 赛: "賽", 车: "車", 通: "通", 讯: "訊", 科: "科",
    学: "學", 区: "區", 号: "號", 广: "廣", 线: "線", 机: "機", 马: "馬",
    桥: "橋", 饼: "餅", 记: "記", 杂: "雜", 园: "園", 岛: "島", 横: "橫",
    风: "風", 顺: "順", 岗: "崗", 顶: "頂", 铺: "鋪", 炉: "爐", 凤: "鳳",
    对: "對", 建: "建", 步: "步", 距: "距", 离: "離", 规: "規",
    划: "劃", 预: "預", 留: "留", 接: "接", 驳: "駁", 题: "題",
    种: "種", 扩: "擴", 充: "充", 节: "節", 点: "點", 实: "實", 时: "時",
    气: "氣", 拥: "擁", 挤: "擠", 进: "進", 境: "境", 勿: "勿", 乘: "乘",
    闸: "閘", 运: "運", 内: "內",
  };
  return [...value].map((character) => characters[character] ?? character).join("");
}

export function localizedPoiName(
  poi: Pick<POI, "poi_id" | "poi_name"> & Partial<Pick<POI, "alias">>,
  language: LanguageCode,
) {
  const id = canonicalId(poi.poi_id);
  const translated = NAMES[id]?.[language] || GENERATED_NAMES[id]?.[language];
  if (translated) return translated;
  if (language === "zh-CN") return poi.poi_name;
  if (language === "zh-TW") return toTraditionalText(poi.poi_name);
  if (poi.alias && !hasHan(poi.alias)) return poi.alias;
  if (!hasHan(poi.poi_name)) return poi.poi_name;
  return latinLabel(poi.poi_name) || poi.poi_name;
}

export function localizedPoiIdName(
  poiId: string,
  language: LanguageCode,
  fallback = "",
) {
  const id = canonicalId(poiId);
  return NAMES[id]?.[language] || GENERATED_NAMES[id]?.[language] || fallback;
}

export function localizedPoiMeta(
  poi: Pick<POI, "category" | "address"> & Partial<Pick<POI, "poi_id">>,
  language: LanguageCode,
) {
  if (poi.poi_id === "poi_port_outer_harbor" || poi.poi_id === "poi_0071") {
    return FERRY_TERMINAL_LABEL[language];
  }
  if (poi.poi_id?.startsWith("poi_port_")) return BORDER_CROSSING_LABEL[language];
  if (language === "zh-CN") return [poi.category, poi.address].filter(Boolean).join(" · ");
  if (language === "zh-TW") {
    const address = toTraditionalText(poi.address);
    const category = CATEGORY_LABELS.find(([pattern]) => pattern.test(poi.category))?.[1][language];
    return [category || META_FALLBACK[language], address].filter(Boolean).join(" · ");
  }
  const category = CATEGORY_LABELS.find(([pattern]) => pattern.test(poi.category))?.[1][language];
  const latinAddress = poi.address && !hasHan(poi.address) ? poi.address : "";
  return [category || META_FALLBACK[language], latinAddress].filter(Boolean).join(" · ");
}

export function localizedPoiSearchText(poi: POI, language: LanguageCode) {
  return `${localizedPoiName(poi, language)} ${poi.poi_name} ${poi.alias ?? ""} ${poi.address} ${poi.category}`;
}
