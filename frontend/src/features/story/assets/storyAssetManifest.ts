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
): StoryAssetManifestItem {
  return { id, src, aspectRatio, fallbackLabel };
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
    "/story/coloane-after-tide/tide-workbook.jpg",
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
);

export const STORY_ASSET_MANIFEST: ReadonlyMap<string, StoryAssetManifestItem> =
  new Map(items.map((item) => [item.id, item]));

export function resolveStoryAsset(
  assetId: string,
): StoryAssetManifestItem | undefined {
  return STORY_ASSET_MANIFEST.get(assetId);
}
