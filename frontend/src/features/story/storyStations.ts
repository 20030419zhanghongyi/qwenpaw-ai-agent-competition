const STORY_STATION_NAMES: Readonly<Record<string, string>> = {
  chapter_ama: "妈阁庙",
  chapter_mandarin_house: "郑家大屋",
  chapter_senado: "议事亭前地",
  chapter_sam_kai: "三街会馆",
  chapter_lou_kau: "卢家大屋",
  chapter_mount_fortress: "大炮台",
  chapter_taipa_sea: "北帝庙",
  chapter_taipa_bell: "嘉模圣母堂",
  chapter_taipa_home: "龙环葡韵",
  chapter_taipa_work: "益隆炮竹厂旧址",
  chapter_taipa_street: "官也街",
  ending_taipa_future_letter: "氹仔旧城公共空间",
  chapter_coloane_sea: "天后古庙／观音古庙",
  chapter_coloane_boat: "谭公庙",
  chapter_coloane_village: "圣方济各圣堂及广场",
  chapter_coloane_craft: "荔枝碗船厂片区",
  chapter_coloane_soil: "黑沙",
  ending_coloane_after_tide: "路环公共空间",
};

export function storyStationName(nodeId: string): string | undefined {
  return STORY_STATION_NAMES[nodeId];
}
