const STORY_STATION_NAMES: Readonly<Record<string, string>> = {
  chapter_ama: "妈阁庙",
  chapter_mandarin_house: "郑家大屋",
  chapter_senado: "议事亭前地",
  chapter_sam_kai: "三街会馆",
  chapter_lou_kau: "卢家大屋",
  chapter_mount_fortress: "大炮台",
};

export function storyStationName(nodeId: string): string | undefined {
  return STORY_STATION_NAMES[nodeId];
}
