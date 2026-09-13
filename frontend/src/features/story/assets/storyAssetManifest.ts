import type { LanguageCode } from "@/types";

export type StoryAssetAspectRatio =
  | "9/16"
  | "3/4"
  | "4/5"
  | "4/3"
  | "2/3"
  | "1/1";

export interface StoryAssetManifestItem {
  id: string;
  src: string;
  aspectRatio: StoryAssetAspectRatio;
  objectPosition?: string;
  fallbackLabel: string;
  creditLabel?: string;
}

const BASE = "/story/v4";

function asset(
  id: string,
  file: string,
  aspectRatio: StoryAssetAspectRatio,
  fallbackLabel: string,
  objectPosition?: string,
): StoryAssetManifestItem {
  return {
    id,
    src: `${BASE}/${file}`,
    aspectRatio,
    fallbackLabel,
    objectPosition,
  };
}

function publicAsset(
  id: string,
  src: string,
  aspectRatio: StoryAssetAspectRatio,
  fallbackLabel: string,
  creditLabel?: string,
): StoryAssetManifestItem {
  return { id, src, aspectRatio, fallbackLabel, creditLabel };
}

const items: StoryAssetManifestItem[] = [
  asset(
    "V4-COVER-01",
    "common/V4-COVER-01_story-cover.webp",
    "9/16",
    "故事封面",
  ),
  asset(
    "V4-ENTRY-01",
    "common/V4-ENTRY-01_story-entry.webp",
    "4/3",
    "故事游邀请",
  ),
  asset(
    "V4-CHAR-01",
    "characters/V4-CHAR-01_alian-neutral.png",
    "2/3",
    "阿莲",
  ),
  asset(
    "V4-CHAR-02",
    "characters/V4-CHAR-02_alian-thinking.png",
    "2/3",
    "阿莲正在查找资料",
  ),
  asset(
    "V4-CHAR-03",
    "characters/V4-CHAR-03_alian-discovery.png",
    "2/3",
    "阿莲发现线索",
  ),
  asset(
    "V4-CHAR-04",
    "characters/V4-CHAR-04_alan-notes.png",
    "2/3",
    "阿澜的回忆",
  ),
  asset(
    "V4-CHAR-05",
    "characters/V4-CHAR-05_m-cartographer.png",
    "2/3",
    "M先生的回忆",
  ),
  asset("V4-PROP-01", "props/V4-PROP-01_old-book.webp", "4/5", "一本旧书"),
  asset(
    "V4-PROP-02",
    "props/V4-PROP-02_envelope.webp",
    "4/5",
    "古书中的旧信封",
  ),
  asset(
    "V4-PROP-03",
    "props/V4-PROP-03_city-double-map.webp",
    "4/5",
    "两张澳门旧图",
  ),
  asset(
    "V4-PROP-04",
    "props/V4-PROP-04_six-local-map-pairs.webp",
    "4/5",
    "六组地点局部图",
  ),
  asset(
    "V4-PROP-05",
    "props/V4-PROP-05_five-notes-stacked.webp",
    "4/5",
    "迎光重合的五张纸条",
  ),
  asset(
    "V4-PRO-01",
    "prologue/V4-PRO-01_book-borrowed.webp",
    "4/5",
    "阿莲借出家藏旧书",
  ),
  asset(
    "V4-PRO-02",
    "prologue/V4-PRO-02_envelope-falls.webp",
    "4/5",
    "信封与地图从书页间滑落",
  ),
  asset(
    "V4-PRO-03",
    "prologue/V4-PRO-03_materials-open.webp",
    "4/5",
    "古书、双图和纸条展开",
  ),
  asset("V4-AMA-01", "ama/V4-AMA-01_arrival.webp", "3/4", "抵达妈阁庙"),
  asset(
    "V4-AMA-02",
    "ama/V4-AMA-02_coast-change.webp",
    "4/5",
    "妈阁庙与海岸变化",
  ),
  asset(
    "V4-AMA-03",
    "ama/V4-AMA-03_double-map.webp",
    "4/5",
    "妈阁庙局部双图",
  ),
  asset("V4-AMA-04", "ama/V4-AMA-04_note-clue.webp", "4/5", "第一张密笺"),
  asset("V4-AMA-05", "ama/V4-AMA-05_reward-petal.png", "1/1", "潮线花瓣"),
  asset(
    "V4-MAN-01",
    "mandarin-house/V4-MAN-01_arrival.webp",
    "3/4",
    "抵达郑家大屋",
  ),
  asset(
    "V4-MAN-02",
    "mandarin-house/V4-MAN-02_turning-path.webp",
    "4/5",
    "郑家大屋的转折动线",
  ),
  asset(
    "V4-MAN-03",
    "mandarin-house/V4-MAN-03_four-elements.webp",
    "4/5",
    "建筑中的四种观察对象",
  ),
  asset(
    "V4-MAN-04",
    "mandarin-house/V4-MAN-04_five-hole-note.webp",
    "4/5",
    "带五个小孔的纸条",
  ),
  asset(
    "V4-MAN-05",
    "mandarin-house/V4-MAN-05_water-lane-map.webp",
    "4/5",
    "水巷局部双图",
  ),
  asset(
    "V4-MAN-06",
    "mandarin-house/V4-MAN-06_reward-petal.png",
    "1/1",
    "水巷花瓣",
  ),
  asset(
    "V4-SEN-01",
    "senado/V4-SEN-01_arrival.webp",
    "3/4",
    "抵达议事亭前地",
  ),
  asset(
    "V4-SEN-02",
    "senado/V4-SEN-02_fountain.webp",
    "4/5",
    "议事亭前地喷水池",
  ),
  asset(
    "V4-SEN-03",
    "senado/V4-SEN-03_wave-paving.webp",
    "4/5",
    "广场的波浪形铺地",
  ),
  asset(
    "V4-SEN-04",
    "senado/V4-SEN-04_old-square-sketch.webp",
    "4/5",
    "旧广场草图",
  ),
  asset(
    "V4-SEN-05",
    "senado/V4-SEN-05_reward-petal.png",
    "1/1",
    "年代花瓣",
  ),
  asset(
    "V4-SAM-01",
    "sam-kai/V4-SAM-01_arrival.webp",
    "3/4",
    "抵达三街会馆",
  ),
  asset(
    "V4-SAM-02",
    "sam-kai/V4-SAM-02_delivery.webp",
    "4/5",
    "货物交付记录",
  ),
  asset("V4-SAM-03", "sam-kai/V4-SAM-03_ledger.webp", "4/5", "店内账簿"),
  asset(
    "V4-SAM-04",
    "sam-kai/V4-SAM-04_porter-receipt.webp",
    "4/5",
    "脚夫留下的存条",
  ),
  asset(
    "V4-SAM-05",
    "sam-kai/V4-SAM-05_three-records.webp",
    "4/5",
    "三份纸面证据",
  ),
  asset(
    "V4-SAM-06",
    "sam-kai/V4-SAM-06_reward-petal.png",
    "1/1",
    "账格花瓣",
  ),
  asset(
    "V4-LOU-01",
    "lou-kau/V4-LOU-01_arrival.webp",
    "3/4",
    "抵达卢家大屋",
  ),
  asset(
    "V4-LOU-02",
    "lou-kau/V4-LOU-02_window-observe.webp",
    "4/5",
    "窗户构造",
  ),
  asset(
    "V4-LOU-03",
    "lou-kau/V4-LOU-03_parts.webp",
    "4/5",
    "窗户构件",
  ),
  asset(
    "V4-LOU-04",
    "lou-kau/V4-LOU-04_assembled-window.webp",
    "4/5",
    "完成拼合的窗户",
  ),
  asset(
    "V4-LOU-05",
    "lou-kau/V4-LOU-05_reward-petal.png",
    "1/1",
    "窗格花瓣",
  ),
  asset(
    "V4-LOU-06",
    "lou-kau/V4-LOU-06_five-notes-light.webp",
    "4/5",
    "五张纸条组成完整市花",
  ),
  asset(
    "V4-FOR-01",
    "mount-fortress/V4-FOR-01_arrival.webp",
    "3/4",
    "抵达大炮台",
  ),
  asset(
    "V4-FOR-02",
    "mount-fortress/V4-FOR-02_city-view.webp",
    "4/5",
    "大炮台上的城市视野",
  ),
  asset(
    "V4-FOR-03",
    "mount-fortress/V4-FOR-03_maps-and-today.webp",
    "4/5",
    "旧图与今日城市重合",
  ),
  asset(
    "V4-FOR-04",
    "mount-fortress/V4-FOR-04_five-evidence.webp",
    "4/5",
    "五站证据",
  ),
  asset(
    "V4-FOR-05",
    "mount-fortress/V4-FOR-05_m-letter.webp",
    "4/5",
    "M先生的回信",
  ),
  asset(
    "V4-FOR-06",
    "mount-fortress/V4-FOR-06_alan-last-note.webp",
    "4/5",
    "阿澜最后的补记",
  ),
  asset(
    "V4-FOR-07",
    "mount-fortress/V4-FOR-07_today-note.webp",
    "4/5",
    "等待书写的今日补记",
  ),
  asset(
    "V4-FOR-08",
    "mount-fortress/V4-FOR-08_complete-flower.png",
    "1/1",
    "完整五瓣市花",
  ),
  asset(
    "V4-FOR-09",
    "mount-fortress/V4-FOR-09_ending-city.webp",
    "9/16",
    "故事结束时的澳门",
  ),
];

items.push(
  asset(
    "V4-LOU-P01",
    "lou-kau/pieces/V4-LOU-P01_upper-frame.png",
    "1/1",
    "上部窗框",
  ),
  asset(
    "V4-LOU-P02",
    "lou-kau/pieces/V4-LOU-P02_lower-frame.png",
    "1/1",
    "下部窗框",
  ),
  asset(
    "V4-LOU-P03",
    "lou-kau/pieces/V4-LOU-P03_oyster-shell-panel.png",
    "1/1",
    "蚝壳窗片",
  ),
  asset(
    "V4-LOU-P04",
    "lou-kau/pieces/V4-LOU-P04_wooden-shutter.png",
    "1/1",
    "木百叶",
  ),
  asset(
    "V4-LOU-P05",
    "lou-kau/pieces/V4-LOU-P05_stained-glass.png",
    "1/1",
    "彩色玻璃",
  ),
  asset(
    "V4-LOU-P06",
    "lou-kau/pieces/V4-LOU-P06_iron-grille.png",
    "1/1",
    "铁花格",
  ),
  asset(
    "V4-LOU-P07",
    "lou-kau/pieces/V4-LOU-P07_aluminum-frame.png",
    "1/1",
    "铝框",
  ),
  asset(
    "V4-LOU-P08",
    "lou-kau/pieces/V4-LOU-P08_stone-lattice.png",
    "1/1",
    "石花格",
  ),
);

items.push(
  publicAsset(
    "CAT-COVER-01",
    "/story/coloane-after-tide/cover.jpg",
    "4/5",
    "《潮退之後》故事封面",
  ),
  publicAsset(
    "CAT-PROP-01",
    "/story/coloane-after-tide/tide-workbook.webp",
    "4/5",
    "潮汐工作簿",
  ),
  publicAsset(
    "CAT-SEA-01",
    "/story/coloane-after-tide/temple.jpg",
    "4/5",
    "路環古廟",
  ),
  publicAsset(
    "CAT-BOAT-01",
    "/story/coloane-after-tide/tam-kung.jpg",
    "4/5",
    "譚公廟與鯨骨龍舟",
  ),
  publicAsset(
    "CAT-VILLAGE-01",
    "/story/coloane-after-tide/chapel-square.jpg",
    "4/5",
    "聖方濟各聖堂廣場",
  ),
  publicAsset(
    "CAT-CRAFT-01",
    "/story/coloane-after-tide/shipyards.jpg",
    "4/5",
    "荔枝碗船廠片區",
  ),
  publicAsset(
    "CAT-SOIL-01",
    "/story/coloane-after-tide/hac-sa.jpg",
    "4/5",
    "黑沙海灘與土地記憶",
  ),
  publicAsset(
    "CAT-END-01",
    "/story/coloane-after-tide/sound-postcard.jpg",
    "4/5",
    "路環聲音明信片",
  ),
  publicAsset(
    "TAI-COVER-01",
    "/story/taipa-letters/TAI-COVER-01_story-cover.jpg",
    "4/3",
    "氹仔旧城与龙环葡韵景观",
    "Rene / CC BY-SA 4.0",
  ),
  publicAsset(
    "TAI-PROP-01",
    "/story/taipa-letters/TAI-PROP-01_returned-letter-box.webp",
    "4/5",
    "退信盒剧情道具",
  ),
  publicAsset(
    "TAI-SEA-01",
    "/story/taipa-letters/TAI-SEA-01_pak-tai-temple.jpg",
    "4/3",
    "氹仔北帝庙外观",
    "LN9267 / CC BY-SA 4.0",
  ),
  publicAsset(
    "TAI-BELL-01",
    "/story/taipa-letters/TAI-BELL-01_carmel-church.jpg",
    "4/3",
    "嘉模圣母堂外观",
    "LN9267 / CC BY-SA 4.0",
  ),
  publicAsset(
    "TAI-HOME-01",
    "/story/taipa-letters/TAI-HOME-01_taipa-houses.jpg",
    "4/3",
    "龙环葡韵住宅式博物馆建筑群",
    "LN9267 / CC BY-SA 4.0",
  ),
  publicAsset(
    "TAI-WORK-01",
    "/story/taipa-letters/TAI-WORK-01_iec-long-firecracker-factory.jpg",
    "4/3",
    "益隆炮竹厂旧址",
    "LN9267 / CC BY-SA 4.0",
  ),
  publicAsset(
    "TAI-STREET-01",
    "/story/taipa-letters/TAI-STREET-01_rua-do-cunha.jpg",
    "4/3",
    "氹仔官也街街景",
    "travel oriented / CC BY-SA 2.0",
  ),
  publicAsset(
    "TAI-END-01",
    "/story/taipa-letters/TAI-END-01_largo-dos-bombeiros.jpg",
    "4/3",
    "氹仔消防局前地街景",
    "LN9267 / CC BY-SA 4.0",
  ),
);

export const STORY_ASSET_MANIFEST: ReadonlyMap<string, StoryAssetManifestItem> =
  new Map(items.map((item) => [item.id, item]));

function labels(zhTW: string, en: string, pt: string) {
  return { "zh-TW": zhTW, en, pt };
}

// Shared portraits and Lotus/Taipa assets use the same locale resolver.
// Coloane-exclusive CAT labels remain part of its separate content workstream.
const LOCALIZED_ASSET_LABELS: Readonly<
  Record<string, Partial<Record<LanguageCode, string>>>
> = {
  "V4-COVER-01": labels("故事封面", "Story cover", "Capa da história"),
  "V4-ENTRY-01": labels("故事遊邀請", "An invitation to the story walk", "Um convite para o passeio narrativo"),
  "V4-CHAR-01": labels("阿蓮", "A Lin", "A Lin"),
  "V4-CHAR-02": labels("阿蓮正在查找資料", "A Lin is checking the sources", "A Lin está a consultar fontes"),
  "V4-CHAR-03": labels("阿蓮發現線索", "A Lin finds a clue", "A Lin encontra uma pista"),
  "V4-CHAR-04": labels("阿瀾的回憶", "A Lan’s memories", "As memórias de A Lan"),
  "V4-CHAR-05": labels("M先生的回憶", "Mr M’s memories", "As memórias do Sr. M"),
  "V4-PROP-01": labels("一本舊書", "An old book", "Um livro antigo"),
  "V4-PROP-02": labels("古書中的舊信封", "An old envelope inside the book", "Um envelope antigo dentro do livro"),
  "V4-PROP-03": labels("兩張澳門舊圖", "Two old maps of Macau", "Dois mapas antigos de Macau"),
  "V4-PROP-04": labels("六組地點局部圖", "Six pairs of local maps", "Seis pares de mapas locais"),
  "V4-PROP-05": labels("迎光重合的五張紙條", "Five notes held together against the light", "Cinco bilhetes sobrepostos à luz"),
  "V4-PRO-01": labels("阿蓮借出家藏舊書", "A Lin lends an old family book", "A Lin empresta um livro antigo da família"),
  "V4-PRO-02": labels("信封與地圖從書頁間滑落", "An envelope and maps slip from the pages", "Um envelope e mapas deslizam de entre as páginas"),
  "V4-PRO-03": labels("古書、雙圖和紙條展開", "The old book, two maps, and notes laid out", "O livro antigo, os dois mapas e os bilhetes abertos"),
  "V4-AMA-01": labels("抵達媽閣廟", "Arriving at A-Ma Temple", "Chegada ao Templo de A-Má"),
  "V4-AMA-02": labels("媽閣廟與海岸變化", "A-Ma Temple and the changing coastline", "O Templo de A-Má e as mudanças da costa"),
  "V4-AMA-03": labels("媽閣廟局部雙圖", "Two local maps of A-Ma Temple", "Dois mapas locais do Templo de A-Má"),
  "V4-AMA-04": labels("第一張密箋", "The first secret note", "O primeiro bilhete secreto"),
  "V4-AMA-05": labels("潮線花瓣", "Shoreline petal", "Pétala da linha de costa"),
  "V4-MAN-01": labels("抵達鄭家大屋", "Arriving at the Mandarin’s House", "Chegada à Casa do Mandarim"),
  "V4-MAN-02": labels("鄭家大屋的轉折動線", "The winding route through the Mandarin’s House", "O percurso sinuoso pela Casa do Mandarim"),
  "V4-MAN-03": labels("建築中的四種觀察對象", "Four architectural features to observe", "Quatro elementos arquitetónicos a observar"),
  "V4-MAN-04": labels("帶五個小孔的紙條", "A note with five small holes", "Um bilhete com cinco pequenos orifícios"),
  "V4-MAN-05": labels("水巷局部雙圖", "Two local maps of the water lane", "Dois mapas locais do corredor de água"),
  "V4-MAN-06": labels("水巷花瓣", "Water-lane petal", "Pétala do corredor de água"),
  "V4-SEN-01": labels("抵達議事亭前地", "Arriving at Senado Square", "Chegada ao Largo do Senado"),
  "V4-SEN-02": labels("議事亭前地噴水池", "The fountain in Senado Square", "A fonte do Largo do Senado"),
  "V4-SEN-03": labels("廣場的波浪形鋪地", "The square’s wave-patterned paving", "A calçada ondulada da praça"),
  "V4-SEN-04": labels("舊廣場草圖", "A sketch of the old square", "Um esboço da antiga praça"),
  "V4-SEN-05": labels("年代花瓣", "Timeline petal", "Pétala das épocas"),
  "V4-SAM-01": labels("抵達三街會館", "Arriving at Sam Kai Vui Kun Temple", "Chegada ao Templo de Sam Kai Vui Kun"),
  "V4-SAM-02": labels("貨物交付記錄", "A goods delivery record", "Um registo de entrega de mercadorias"),
  "V4-SAM-03": labels("店內帳簿", "The shop ledger", "O livro de contas da loja"),
  "V4-SAM-04": labels("腳夫留下的存條", "The porter’s receipt", "O recibo deixado pelo carregador"),
  "V4-SAM-05": labels("三份紙面證據", "Three pieces of written evidence", "Três documentos de prova"),
  "V4-SAM-06": labels("帳格花瓣", "Ledger petal", "Pétala do livro de contas"),
  "V4-LOU-01": labels("抵達盧家大屋", "Arriving at Lou Kau Mansion", "Chegada à Casa de Lou Kau"),
  "V4-LOU-02": labels("窗戶構造", "The structure of the window", "A estrutura da janela"),
  "V4-LOU-03": labels("窗戶構件", "Window components", "Componentes da janela"),
  "V4-LOU-04": labels("完成拼合的窗戶", "The assembled window", "A janela montada"),
  "V4-LOU-05": labels("窗格花瓣", "Window-lattice petal", "Pétala da gelosia"),
  "V4-LOU-06": labels("五張紙條組成完整市花", "Five notes form the complete city flower", "Cinco bilhetes formam a flor completa da cidade"),
  "V4-LOU-P01": labels("上部窗框", "Upper window frame", "Parte superior da moldura"),
  "V4-LOU-P02": labels("下部窗框", "Lower window frame", "Parte inferior da moldura"),
  "V4-LOU-P03": labels("蠔殼窗片", "Oyster-shell window panel", "Painel de conchas de ostra"),
  "V4-LOU-P04": labels("木百葉", "Wooden shutter", "Persiana de madeira"),
  "V4-LOU-P05": labels("彩色玻璃", "Stained glass", "Vidro colorido"),
  "V4-LOU-P06": labels("鐵花格", "Decorative iron grille", "Grade decorativa de ferro"),
  "V4-LOU-P07": labels("鋁框", "Aluminium frame", "Moldura de alumínio"),
  "V4-LOU-P08": labels("石花格", "Stone lattice", "Gelosia de pedra"),
  "V4-FOR-01": labels("抵達大炮台", "Arriving at Mount Fortress", "Chegada à Fortaleza do Monte"),
  "V4-FOR-02": labels("大炮台上的城市視野", "The city seen from Mount Fortress", "A cidade vista da Fortaleza do Monte"),
  "V4-FOR-03": labels("舊圖與今日城市重合", "Old maps overlaid on today’s city", "Mapas antigos sobrepostos à cidade de hoje"),
  "V4-FOR-04": labels("五站證據", "Evidence from five stops", "Provas recolhidas em cinco paragens"),
  "V4-FOR-05": labels("M先生的回信", "Mr M’s reply", "A resposta do Sr. M"),
  "V4-FOR-06": labels("阿瀾最後的補記", "A Lan’s final note", "A última nota de A Lan"),
  "V4-FOR-07": labels("等待書寫的今日補記", "A blank page for today’s note", "Uma página em branco para a nota de hoje"),
  "V4-FOR-08": labels("完整五瓣市花", "The complete five-petalled city flower", "A flor completa da cidade, com cinco pétalas"),
  "V4-FOR-09": labels("故事結束時的澳門", "Macau at the close of the story", "Macau no final da história"),
  "TAI-COVER-01": labels("氹仔舊城與龍環葡韻景觀", "Taipa’s old town and the Taipa Houses", "O centro antigo da Taipa e as Casas da Taipa"),
  "TAI-PROP-01": labels("退信盒劇情道具", "The returned-letter box — a story prop", "A caixa de cartas devolvidas — um objeto da história"),
  "TAI-SEA-01": labels("氹仔北帝廟外觀", "The exterior of Pak Tai Temple in Taipa", "O exterior do Templo de Pak Tai, na Taipa"),
  "TAI-BELL-01": labels("嘉模聖母堂外觀", "The exterior of Our Lady of Carmel Church", "O exterior da Igreja de Nossa Senhora do Carmo"),
  "TAI-HOME-01": labels("龍環葡韻住宅式博物館建築群", "The Taipa Houses museum buildings", "O conjunto museológico das Casas da Taipa"),
  "TAI-WORK-01": labels("益隆炮竹廠舊址", "The former Iec Long Firecracker Factory", "A Antiga Fábrica de Panchões I Long"),
  "TAI-STREET-01": labels("氹仔官也街街景", "A street view of Rua do Cunha in Taipa", "Vista da Rua do Cunha, na Taipa"),
  "TAI-END-01": labels("氹仔消防局前地街景", "A street view of Largo dos Bombeiros in Taipa", "Vista do Largo dos Bombeiros, na Taipa"),
};

export function resolveStoryAsset(
  assetId: string,
  language: LanguageCode = "zh-CN",
): StoryAssetManifestItem | undefined {
  const item = STORY_ASSET_MANIFEST.get(assetId);
  const label = LOCALIZED_ASSET_LABELS[assetId]?.[language];
  return item && label ? { ...item, fallbackLabel: label } : item;
}
