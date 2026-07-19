import { load } from "@amap/amap-jsapi-loader";
import { useEffect, useRef, useState } from "react";
import { fetchRoutePois, fetchRouteWalkPath } from "@/api/routes";
import { useWalk } from "@/state/WalkContext";
import type { LanguageCode } from "@/types";

interface MapRouteViewProps {
  poiIds: string[];
  currentPoiId?: string;
  onSelectPoi?: (poiId: string) => void;
}

interface AMapInstance {
  add: (overlays: unknown | unknown[]) => void;
  destroy: () => void;
  setFitView: (
    overlays?: unknown[],
    immediately?: boolean,
    avoid?: [number, number, number, number],
    maxZoom?: number,
  ) => void;
}

interface AMapMarker {
  on: (event: string, handler: () => void) => void;
  setContent: (content: string) => void;
}

interface AMapNamespace {
  Map: new (
    container: HTMLElement,
    options: {
      center: [number, number];
      zoom: number;
      viewMode: string;
      resizeEnable: boolean;
    },
  ) => AMapInstance;
  Marker: new (options: {
    position: [number, number];
    title: string;
    anchor: string;
    content: string;
    zIndex: number;
  }) => AMapMarker;
  Polyline: new (options: {
    path: Array<[number, number]>;
    strokeColor: string;
    strokeWeight: number;
    strokeOpacity: number;
    lineJoin: string;
    lineCap: string;
    zIndex: number;
  }) => unknown;
}

declare global {
  interface Window {
    _AMapSecurityConfig?: {
      securityJsCode: string;
    };
  }
}

const COPY: Record<
  LanguageCode,
  {
    loading: string;
    missingKey: string;
    loadFailed: string;
    pathFailed: string;
    noStops: string;
  }
> = {
  "zh-CN": {
    loading: "正在加载真实地图…",
    missingKey: "地图尚未配置，请设置高德 Web 端 Key。",
    loadFailed: "地图暂时无法加载，行程列表仍可正常使用。",
    pathFailed: "步行路线暂不可用，已保留真实地点标记。",
    noStops: "当前路线没有可显示的地点。",
  },
  "zh-TW": {
    loading: "正在載入真實地圖…",
    missingKey: "地圖尚未設定，請配置高德 Web 端 Key。",
    loadFailed: "地圖暫時無法載入，行程列表仍可正常使用。",
    pathFailed: "步行路線暫不可用，已保留真實地點標記。",
    noStops: "目前路線沒有可顯示的地點。",
  },
  en: {
    loading: "Loading the live map…",
    missingKey: "Map key is not configured.",
    loadFailed: "Map unavailable. The itinerary remains available.",
    pathFailed: "Walking path unavailable; real stop markers are still shown.",
    noStops: "This route has no mappable stops.",
  },
  pt: {
    loading: "A carregar o mapa real…",
    missingKey: "A chave do mapa não está configurada.",
    loadFailed: "Mapa indisponível. O itinerário continua acessível.",
    pathFailed: "Percurso indisponível; os marcadores reais continuam visíveis.",
    noStops: "Este percurso não tem paragens para mostrar.",
  },
};

function parsePolyline(polyline: string): Array<[number, number]> {
  return polyline
    .split(";")
    .map((pair) => pair.split(","))
    .filter((parts) => parts.length === 2)
    .map(([lng, lat]) => [Number(lng), Number(lat)] as [number, number])
    .filter(([lng, lat]) => Number.isFinite(lng) && Number.isFinite(lat));
}

function markerContent(order: number, current: boolean): string {
  const size = current ? 42 : 32;
  const background = current ? "#526454" : "#f7f1e5";
  const color = current ? "#fffaf0" : "#526454";
  const ring = current ? "0 0 0 4px rgba(82,100,84,.2)" : "0 0 0 2px #fffaf0";
  return [
    `<div style="width:${size}px;height:${size}px;border-radius:999px;`,
    `display:grid;place-items:center;background:${background};color:${color};`,
    `border:3px solid #fffaf0;box-shadow:${ring},0 6px 18px rgba(47,49,40,.2);`,
    `font:700 12px Georgia,serif;cursor:pointer">${order}</div>`,
  ].join("");
}

export function MapRouteView({
  poiIds,
  currentPoiId,
  onSelectPoi,
}: MapRouteViewProps) {
  const { language } = useWalk();
  const copy = COPY[language];
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<AMapInstance | null>(null);
  const markersRef = useRef(new Map<string, { marker: AMapMarker; order: number }>());
  const onSelectRef = useRef(onSelectPoi);
  const currentPoiRef = useRef(currentPoiId);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const poiKey = poiIds.join("|");
  const stablePoiIds = poiKey ? poiKey.split("|") : [];

  useEffect(() => {
    onSelectRef.current = onSelectPoi;
  }, [onSelectPoi]);

  useEffect(() => {
    currentPoiRef.current = currentPoiId;
    for (const [poiId, entry] of markersRef.current) {
      entry.marker.setContent(markerContent(entry.order, poiId === currentPoiId));
    }
  }, [currentPoiId]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const key = import.meta.env.VITE_AMAP_API_KEY?.trim();
    const securityCode = import.meta.env.VITE_AMAP_SECURITY_CODE?.trim();
    const controller = new AbortController();
    let cancelled = false;
    let createdMap: AMapInstance | null = null;

    setLoading(true);
    setError(null);
    setWarning(null);
    markersRef.current.clear();

    if (!key) {
      setLoading(false);
      setError(copy.missingKey);
      return () => controller.abort();
    }
    if (securityCode) {
      window._AMapSecurityConfig = { securityJsCode: securityCode };
    }

    void (async () => {
      try {
        const [namespace, pois] = await Promise.all([
          load({ key, version: "2.0", plugins: [] }) as Promise<AMapNamespace>,
          fetchRoutePois(stablePoiIds, controller.signal),
        ]);
        if (cancelled) return;
        if (pois.length === 0) {
          setError(copy.noStops);
          return;
        }

        createdMap = new namespace.Map(container, {
          center: [pois[0].longitude, pois[0].latitude],
          zoom: 15,
          viewMode: "2D",
          resizeEnable: true,
        });
        mapRef.current = createdMap;

        const overlays: unknown[] = [];
        for (const [index, poi] of pois.entries()) {
          const marker = new namespace.Marker({
            position: [poi.longitude, poi.latitude],
            title: poi.poi_name,
            anchor: "center",
            content: markerContent(index + 1, poi.poi_id === currentPoiRef.current),
            zIndex: poi.poi_id === currentPoiId ? 130 : 120,
          });
          marker.on("click", () => onSelectRef.current?.(poi.poi_id));
          markersRef.current.set(poi.poi_id, { marker, order: index + 1 });
          overlays.push(marker);
        }

        if (stablePoiIds.length >= 2) {
          try {
            const pathResult = await fetchRouteWalkPath(stablePoiIds);
            if (!cancelled) {
              const path = parsePolyline(pathResult.polyline);
              if (path.length >= 2) {
                overlays.unshift(
                  new namespace.Polyline({
                    path,
                    strokeColor: "#526454",
                    strokeWeight: 6,
                    strokeOpacity: 0.9,
                    lineJoin: "round",
                    lineCap: "round",
                    zIndex: 110,
                  }),
                );
              } else {
                setWarning(copy.pathFailed);
              }
            }
          } catch {
            if (!cancelled) setWarning(copy.pathFailed);
          }
        }

        if (cancelled) return;
        createdMap.add(overlays);
        createdMap.setFitView(overlays, false, [64, 64, 92, 64], 17);
      } catch (reason) {
        if (cancelled || controller.signal.aborted) return;
        const message =
          reason instanceof Error && reason.message.includes("AMap")
            ? `${copy.loadFailed} ${reason.message}`
            : copy.loadFailed;
        setError(message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
      markersRef.current.clear();
      if (createdMap) createdMap.destroy();
      if (mapRef.current === createdMap) mapRef.current = null;
    };
  }, [copy.loadFailed, copy.missingKey, copy.noStops, copy.pathFailed, poiKey]);

  return (
    <div className="absolute inset-0 bg-paper-warm">
      <div ref={containerRef} className="h-full w-full" aria-label="route map" />
      {loading ? (
        <div className="pointer-events-none absolute inset-0 grid place-items-center bg-paper-warm/90">
          <p className="rounded-full border border-line bg-paper px-4 py-2 text-sm text-ink-soft shadow-[var(--shadow-soft)]">
            {copy.loading}
          </p>
        </div>
      ) : null}
      {error ? (
        <div className="absolute inset-0 grid place-items-center bg-paper-warm px-6 text-center">
          <div className="max-w-sm rounded-2xl border border-clay/30 bg-paper p-5 shadow-[var(--shadow-soft)]">
            <p className="text-sm leading-relaxed text-clay">{error}</p>
          </div>
        </div>
      ) : null}
      {warning && !error ? (
        <div className="pointer-events-none absolute left-1/2 top-5 z-10 w-[calc(100%-2.5rem)] max-w-sm -translate-x-1/2 rounded-2xl border border-ochre/30 bg-paper/95 px-4 py-3 text-xs text-ink shadow-[var(--shadow-soft)]">
          {warning}
        </div>
      ) : null}
    </div>
  );
}
