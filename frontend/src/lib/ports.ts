/** Border-crossing catalog aligned with data/ports.json. */

import type { Preference, RouteNode } from "@/types";

export interface PortOption {
  poiId: string;
  nameZh: string;
  nameEn: string;
  alias: string;
}

export const PORT_OPTIONS: PortOption[] = [
  { poiId: "poi_port_guanja", nameZh: "关闸口岸", nameEn: "Portas do Cerco", alias: "关闸" },
  { poiId: "poi_port_qingmao", nameZh: "青茂口岸", nameEn: "Qingmao Port", alias: "青茂" },
  { poiId: "poi_port_hengqin", nameZh: "横琴口岸", nameEn: "Hengqin Port", alias: "横琴" },
  { poiId: "poi_port_hzmb", nameZh: "港珠澳大桥口岸", nameEn: "HZMB Port", alias: "港珠澳" },
  {
    poiId: "poi_port_outer_harbor",
    nameZh: "外港客运码头",
    nameEn: "Outer Harbour",
    alias: "外港",
  },
  { poiId: "poi_0071", nameZh: "内港客运码头", nameEn: "Inner Harbour", alias: "内港" },
];

export function portLabel(poiId: string | null | undefined, language: string): string {
  const port = PORT_OPTIONS.find((item) => item.poiId === poiId);
  if (!port) return poiId || "";
  if (language === "en" || language === "pt") return port.nameEn;
  return port.nameZh;
}

/** Local transfer tip when backend route was matched without port anchors. */
export function entryPortTransferNote(
  entryPort: string | null | undefined,
  language: string,
): string {
  const name = portLabel(entryPort, language);
  if (language === "en" || language === "pt") {
    return `${name}: take a bus or resort shuttle to Cotai — do not plan this leg as a walk. Allow 30–50 min for immigration and transfer.`;
  }
  if (language === "zh-TW") {
    return `${name}至路氹不宜按步行排線：出關後可乘巴士或度假區穿梭巴士，建議預留 30–50 分鐘通關與接駁。`;
  }
  return `${name}至路氹度假区不宜按步行排线：出关后可乘澳门巴士或度假区穿梭巴士前往，建议预留 30–50 分钟通关与接驳。`;
}

/**
 * Ensure preference entry/exit ports appear as fixed anchors even when the
 * saved match was produced without them (stale session / prefs saved later).
 */
export function ensurePreferencePortAnchors(
  nodes: RouteNode[],
  preference: Preference | null | undefined,
  language: string,
): RouteNode[] {
  const sorted = [...(nodes ?? [])].sort((a, b) => a.order - b.order);
  const entry = preference?.entry_port?.trim() || null;
  const exit = preference?.exit_port?.trim() || null;
  if (!entry && !exit) return sorted;

  const middle = sorted.filter(
    (node) =>
      node.anchor !== "entry" &&
      node.anchor !== "exit" &&
      node.poi_id !== entry &&
      node.poi_id !== exit,
  );

  const result: RouteNode[] = [];
  const existingEntry = sorted.find(
    (node) => node.anchor === "entry" || (entry && node.poi_id === entry),
  );
  if (entry) {
    result.push(
      existingEntry
        ? {
            ...existingEntry,
            anchor: "entry",
            note:
              existingEntry.note?.includes("巴士") || existingEntry.note?.includes("shuttle")
                ? existingEntry.note
                : entryPortTransferNote(entry, language),
          }
        : {
            poi_id: entry,
            order: 1,
            suggested_stay_min: 20,
            note: entryPortTransferNote(entry, language),
            replaceable_with: [],
            anchor: "entry",
          },
    );
  }

  result.push(...middle);

  const existingExit = sorted.find(
    (node) => node.anchor === "exit" || (exit && node.poi_id === exit),
  );
  if (exit) {
    result.push(
      existingExit
        ? { ...existingExit, anchor: "exit" }
        : {
            poi_id: exit,
            order: result.length + 1,
            suggested_stay_min: 20,
            note: language.startsWith("zh") ? "出境口岸 · 行程终点" : "Exit port · end of day",
            replaceable_with: [],
            anchor: "exit",
          },
    );
  }

  return result.map((node, index) => ({ ...node, order: index + 1 }));
}
