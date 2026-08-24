import { load } from "@amap/amap-jsapi-loader";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { fetchRoutePois, fetchRouteWalkPath } from "@/api/routes";
import { useWalk } from "@/state/WalkContext";
import type { LanguageCode } from "@/types";
import type { RoutePoi } from "@/types/routes";

const LeafletRouteFallback = lazy(() =>
  import("@/components/map/LeafletRouteFallback").then((module) => ({
    default: module.LeafletRouteFallback,
  })),
);

export interface MapUserLocation {
  latitude: number;
  longitude: number;
}

interface MapRouteViewProps {
  poiIds: string[];
  currentPoiId?: string;
  onSelectPoi?: (poiId: string) => void;
  /** Optional story-specific display labels keyed by POI id. */
  poiLabels?: Record<string, string>;
  /** Live user GPS; shown as a distinct blue-dot marker when present. */
  userLocation?: MapUserLocation | null;
  /** Increment to pan/center the map on the current userLocation. */
  recenterToken?: number;
}

interface AMapInstance {
  add: (overlays: unknown | unknown[]) => void;
  remove: (overlays: unknown | unknown[]) => void;
  destroy: () => void;
  setCenter: (center: [number, number]) => void;
  setZoom: (zoom: number) => void;
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
  setPosition: (position: [number, number]) => void;
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
    dataFailed: string;
    fallbackActive: string;
    pathFailed: string;
    noStops: string;
  }
> = {
  "zh-CN": {
    loading: "正在加载真实地图…",
    missingKey: "地图尚未配置，请设置高德 Web 端 Key。",
    loadFailed: "地图暂时无法加载，行程列表仍可正常使用。",
    dataFailed: "地图地点数据暂时无法读取，请稍后重试。",
    fallbackActive: "高德地图连接失败，已切换至备用地图。",
    pathFailed: "步行路线暂不可用，已保留真实地点标记。",
    noStops: "当前路线没有可显示的地点。",
  },
  "zh-TW": {
    loading: "正在載入真實地圖…",
    missingKey: "地圖尚未設定，請配置高德 Web 端 Key。",
    loadFailed: "地圖暫時無法載入，行程列表仍可正常使用。",
    dataFailed: "地圖地點資料暫時無法讀取，請稍後再試。",
    fallbackActive: "高德地圖連線失敗，已切換至備用地圖。",
    pathFailed: "步行路線暫不可用，已保留真實地點標記。",
    noStops: "目前路線沒有可顯示的地點。",
  },
  en: {
    loading: "Loading the live map…",
    missingKey: "Map key is not configured.",
    loadFailed: "Map unavailable. The itinerary remains available.",
    dataFailed: "Map stop data is temporarily unavailable. Please try again shortly.",
    fallbackActive: "AMap could not connect; the backup map is now in use.",
    pathFailed: "Walking path unavailable; real stop markers are still shown.",
    noStops: "This route has no mappable stops.",
  },
  pt: {
    loading: "A carregar o mapa real…",
    missingKey: "A chave do mapa não está configurada.",
    loadFailed: "Mapa indisponível. O itinerário continua acessível.",
    dataFailed: "Os dados das paragens estão temporariamente indisponíveis.",
    fallbackActive: "Não foi possível ligar ao AMap; está a ser usado o mapa alternativo.",
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

function userMarkerContent(): string {
  return [
    `<div style="position:relative;width:22px;height:22px;">`,
    `<div style="position:absolute;inset:-8px;border-radius:999px;`,
    `background:rgba(37,99,235,.22);animation:map-user-pulse 1.8s ease-out infinite"></div>`,
    `<div style="position:relative;width:22px;height:22px;border-radius:999px;`,
    `background:#2563eb;border:3px solid #fffaf0;`,
    `box-shadow:0 0 0 2px rgba(37,99,235,.35),0 4px 12px rgba(47,49,40,.25)"></div>`,
    `</div>`,
  ].join("");
}

export function MapRouteView({
  poiIds,
  currentPoiId,
  onSelectPoi,
  poiLabels,
  userLocation = null,
  recenterToken = 0,
}: MapRouteViewProps) {
  const { language } = useWalk();
  const copy = COPY[language];
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<AMapInstance | null>(null);
  const amapRef = useRef<AMapNamespace | null>(null);
  const markersRef = useRef(new Map<string, { marker: AMapMarker; order: number }>());
  const userMarkerRef = useRef<AMapMarker | null>(null);
  const onSelectRef = useRef(onSelectPoi);
  const currentPoiRef = useRef(currentPoiId);
  const userLocationRef = useRef(userLocation);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [fallbackMap, setFallbackMap] = useState<{
    pois: RoutePoi[];
    path: Array<[number, number]>;
  } | null>(null);
  const [preferFallback, setPreferFallback] = useState(false);
  const [mapReadyTick, setMapReadyTick] = useState(0);
  const poiKey = poiIds.join("|");
  const poiLabelKey = JSON.stringify(poiLabels ?? {});
  const stablePoiIds = poiKey ? poiKey.split("|") : [];

  useEffect(() => {
    onSelectRef.current = onSelectPoi;
  }, [onSelectPoi]);

  useEffect(() => {
    userLocationRef.current = userLocation;
  }, [userLocation]);

  useEffect(() => {
    currentPoiRef.current = currentPoiId;
    for (const [poiId, entry] of markersRef.current) {
      entry.marker.setContent(markerContent(entry.order, poiId === currentPoiId));
    }
  }, [currentPoiId]);

  useEffect(() => {
    if (mapReadyTick > 0 || fallbackMap) return;
    const timer = window.setTimeout(() => setPreferFallback(true), 7000);
    return () => window.clearTimeout(timer);
  }, [fallbackMap, mapReadyTick]);

  useEffect(() => {
    const map = mapRef.current;
    const AMap = amapRef.current;
    if (!map || !AMap || mapReadyTick === 0) return;

    if (
      !userLocation ||
      !Number.isFinite(userLocation.latitude) ||
      !Number.isFinite(userLocation.longitude)
    ) {
      if (userMarkerRef.current) {
        map.remove(userMarkerRef.current);
        userMarkerRef.current = null;
      }
      return;
    }

    const position: [number, number] = [userLocation.longitude, userLocation.latitude];
    if (userMarkerRef.current) {
      userMarkerRef.current.setPosition(position);
      return;
    }

    const marker = new AMap.Marker({
      position,
      title: "You",
      anchor: "center",
      content: userMarkerContent(),
      zIndex: 200,
    });
    map.add(marker);
    userMarkerRef.current = marker;
  }, [userLocation, mapReadyTick]);

  useEffect(() => {
    if (!recenterToken) return;
    const map = mapRef.current;
    if (
      !map ||
      !userLocation ||
      !Number.isFinite(userLocation.latitude) ||
      !Number.isFinite(userLocation.longitude)
    ) {
      return;
    }
    map.setCenter([userLocation.longitude, userLocation.latitude]);
    map.setZoom(16);
  }, [recenterToken, userLocation]);

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
    setFallbackMap(null);
    setMapReadyTick(0);
    markersRef.current.clear();
    userMarkerRef.current = null;
    amapRef.current = null;

    if (securityCode) {
      window._AMapSecurityConfig = { securityJsCode: securityCode };
    }

    void (async () => {
      let pois: RoutePoi[];
      try {
        pois = await fetchRoutePois(stablePoiIds, controller.signal);
      } catch {
        if (!cancelled && !controller.signal.aborted) setError(copy.dataFailed);
        if (!cancelled) setLoading(false);
        return;
      }
      if (cancelled) return;
      if (pois.length === 0) {
        setError(copy.noStops);
        setLoading(false);
        return;
      }

      const activateFallback = (notice: string) => {
        setFallbackMap({ pois, path: [] });
        setWarning(notice);
        setLoading(false);

        if (stablePoiIds.length >= 2) {
          void fetchRouteWalkPath(stablePoiIds).then(
            (result) => {
              if (!cancelled) {
                setFallbackMap({ pois, path: parsePolyline(result.polyline) });
              }
            },
            () => {
              if (!cancelled) setWarning(copy.pathFailed);
            },
          );
        }
      };

      if (!key || preferFallback) {
        activateFallback(key ? copy.fallbackActive : copy.missingKey);
        return;
      }

      let namespace: AMapNamespace;
      try {
        namespace = await Promise.race([
          load({ key, version: "2.0", plugins: [] }) as Promise<AMapNamespace>,
          new Promise<never>((_, reject) =>
            window.setTimeout(() => reject(new Error("AMap load timeout")), 7000),
          ),
        ]);
      } catch {
        if (cancelled) return;
        activateFallback(copy.fallbackActive);
        return;
      }

      try {
        if (cancelled) return;

        createdMap = new namespace.Map(container, {
          center: [pois[0].longitude, pois[0].latitude],
          zoom: 15,
          viewMode: "2D",
          resizeEnable: true,
        });
        mapRef.current = createdMap;
        amapRef.current = namespace;
        setMapReadyTick((tick) => tick + 1);

        const overlays: unknown[] = [];
        const liveUser = userLocationRef.current;
        if (
          liveUser &&
          Number.isFinite(liveUser.latitude) &&
          Number.isFinite(liveUser.longitude)
        ) {
          const userMarker = new namespace.Marker({
            position: [liveUser.longitude, liveUser.latitude],
            title: "You",
            anchor: "center",
            content: userMarkerContent(),
            zIndex: 200,
          });
          userMarkerRef.current = userMarker;
          overlays.push(userMarker);
        }
        for (const [index, poi] of pois.entries()) {
          const displayName = poiLabels?.[poi.poi_id] ?? poi.poi_name;
          const marker = new namespace.Marker({
            position: [poi.longitude, poi.latitude],
            title: displayName,
            anchor: "center",
            content: markerContent(index + 1, poi.poi_id === currentPoiRef.current),
            zIndex: poi.poi_id === currentPoiId ? 130 : 120,
          });
          marker.on("click", () => onSelectRef.current?.(poi.poi_id));
          markersRef.current.set(poi.poi_id, { marker, order: index + 1 });
          overlays.push(marker);
        }

        if (cancelled) return;
        createdMap.add(overlays);
        createdMap.setFitView(overlays, false, [64, 64, 92, 64], 17);
        setLoading(false);

        if (stablePoiIds.length >= 2) {
          try {
            const pathResult = await fetchRouteWalkPath(stablePoiIds);
            if (!cancelled) {
              const path = parsePolyline(pathResult.polyline);
              if (path.length >= 2) {
                const routeLine = new namespace.Polyline({
                  path,
                  strokeColor: "#526454",
                  strokeWeight: 6,
                  strokeOpacity: 0.9,
                  lineJoin: "round",
                  lineCap: "round",
                  zIndex: 110,
                });
                createdMap.add(routeLine);
                createdMap.setFitView([routeLine, ...overlays], false, [64, 64, 92, 64], 17);
              } else {
                setWarning(copy.pathFailed);
              }
            }
          } catch {
            if (!cancelled) setWarning(copy.pathFailed);
          }
        }

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
      userMarkerRef.current = null;
      amapRef.current = null;
      if (createdMap) createdMap.destroy();
      if (mapRef.current === createdMap) mapRef.current = null;
    };
  }, [
    copy.loadFailed,
    copy.dataFailed,
    copy.fallbackActive,
    copy.missingKey,
    copy.noStops,
    copy.pathFailed,
    preferFallback,
    poiKey,
    poiLabelKey,
  ]);

  return (
    <div className="map-route-view absolute inset-0 z-0 overflow-hidden bg-paper-warm [contain:paint]">
      <style>{`@keyframes map-user-pulse{0%{transform:scale(.7);opacity:.55}70%{transform:scale(1.35);opacity:0}100%{transform:scale(1.35);opacity:0}}`}</style>
      {fallbackMap ? (
        <Suspense fallback={null}>
          <LeafletRouteFallback
            pois={fallbackMap.pois}
            path={fallbackMap.path}
            currentPoiId={currentPoiId}
            poiLabels={poiLabels}
            userLocation={userLocation}
            recenterToken={recenterToken}
            onSelectPoi={onSelectPoi}
          />
        </Suspense>
      ) : (
        <div ref={containerRef} className="h-full w-full" aria-label="route map" />
      )}
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
