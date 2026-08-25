import L, { type Map as LeafletMap, type Marker } from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";
import type { RoutePoi } from "@/types/routes";
import type { MapUserLocation } from "./MapRouteView";

interface LeafletRouteFallbackProps {
  pois: RoutePoi[];
  path: Array<[number, number]>;
  currentPoiId?: string;
  poiLabels?: Record<string, string>;
  userLocation?: MapUserLocation | null;
  recenterToken?: number;
  onSelectPoi?: (poiId: string) => void;
}

function transformLatitude(x: number, y: number) {
  let result = -100 + 2 * x + 3 * y + 0.2 * y ** 2 + 0.1 * x * y;
  result += 0.2 * Math.sqrt(Math.abs(x));
  result += ((20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2) / 3;
  result += ((20 * Math.sin(y * Math.PI) + 40 * Math.sin((y / 3) * Math.PI)) * 2) / 3;
  result += ((160 * Math.sin((y / 12) * Math.PI) + 320 * Math.sin((y * Math.PI) / 30)) * 2) / 3;
  return result;
}

function transformLongitude(x: number, y: number) {
  let result = 300 + x + 2 * y + 0.1 * x ** 2 + 0.1 * x * y;
  result += 0.1 * Math.sqrt(Math.abs(x));
  result += ((20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2) / 3;
  result += ((20 * Math.sin(x * Math.PI) + 40 * Math.sin((x / 3) * Math.PI)) * 2) / 3;
  result += ((150 * Math.sin((x / 12) * Math.PI) + 300 * Math.sin((x / 30) * Math.PI)) * 2) / 3;
  return result;
}

function gcj02ToWgs84(latitude: number, longitude: number): [number, number] {
  const earthRadius = 6378245;
  const eccentricity = 0.006693421622965943;
  const deltaLatitude = transformLatitude(longitude - 105, latitude - 35);
  const deltaLongitude = transformLongitude(longitude - 105, latitude - 35);
  const radians = (latitude / 180) * Math.PI;
  const magic = 1 - eccentricity * Math.sin(radians) ** 2;
  const squareRoot = Math.sqrt(magic);
  const adjustedLatitude =
    latitude +
    (deltaLatitude * 180) /
      (((earthRadius * (1 - eccentricity)) / (magic * squareRoot)) * Math.PI);
  const adjustedLongitude =
    longitude +
    (deltaLongitude * 180) /
      (((earthRadius / squareRoot) * Math.cos(radians)) * Math.PI);
  return [latitude * 2 - adjustedLatitude, longitude * 2 - adjustedLongitude];
}

function stopIcon(order: number, current: boolean) {
  const size = current ? 42 : 32;
  const background = current ? "#526454" : "#fffaf0";
  const color = current ? "#fffaf0" : "#526454";
  return L.divIcon({
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div style="display:grid;place-items:center;width:100%;height:100%;border-radius:999px;border:3px solid #fffaf0;background:${background};color:${color};font:700 12px Georgia,serif;box-shadow:0 6px 18px rgba(47,49,40,.25)">${order}</div>`,
  });
}

function userIcon() {
  return L.divIcon({
    className: "",
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    html: '<div style="width:24px;height:24px;border-radius:999px;border:3px solid #fffaf0;background:#2563eb;box-shadow:0 0 0 4px rgba(37,99,235,.25),0 6px 18px rgba(47,49,40,.25)"></div>',
  });
}

export function LeafletRouteFallback({
  pois,
  path,
  currentPoiId,
  poiLabels,
  userLocation,
  recenterToken = 0,
  onSelectPoi,
}: LeafletRouteFallbackProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const markersRef = useRef(new Map<string, Marker>());
  const userMarkerRef = useRef<Marker | null>(null);
  const onSelectRef = useRef(onSelectPoi);

  useEffect(() => {
    onSelectRef.current = onSelectPoi;
  }, [onSelectPoi]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || pois.length === 0) return;
    const first = gcj02ToWgs84(pois[0].latitude, pois[0].longitude);
    const map = L.map(container, { zoomControl: false, attributionControl: true }).setView(first, 14);
    mapRef.current = map;
    L.control.zoom({ position: "topright" }).addTo(map);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    const bounds = L.latLngBounds([]);
    pois.forEach((poi, index) => {
      const position = gcj02ToWgs84(poi.latitude, poi.longitude);
      const marker = L.marker(position, {
        icon: stopIcon(index + 1, poi.poi_id === currentPoiId),
        title: poiLabels?.[poi.poi_id] ?? poi.poi_name,
      }).on("click", () => onSelectRef.current?.(poi.poi_id));
      marker.addTo(map);
      markersRef.current.set(poi.poi_id, marker);
      bounds.extend(position);
    });
    if (path.length >= 2) {
      const convertedPath = path.map(([longitude, latitude]) =>
        gcj02ToWgs84(latitude, longitude),
      );
      L.polyline(convertedPath, { color: "#526454", weight: 6, opacity: 0.9 }).addTo(map);
      convertedPath.forEach((position) => bounds.extend(position));
    }
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [48, 48], maxZoom: 17 });
    window.setTimeout(() => map.invalidateSize(), 0);

    return () => {
      markersRef.current.clear();
      userMarkerRef.current = null;
      map.remove();
      mapRef.current = null;
    };
  }, [path, poiLabels, pois]);

  useEffect(() => {
    pois.forEach((poi, index) => {
      markersRef.current
        .get(poi.poi_id)
        ?.setIcon(stopIcon(index + 1, poi.poi_id === currentPoiId));
    });
  }, [currentPoiId, pois]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (!userLocation) {
      if (userMarkerRef.current) map.removeLayer(userMarkerRef.current);
      userMarkerRef.current = null;
      return;
    }
    const position: [number, number] = [userLocation.latitude, userLocation.longitude];
    if (userMarkerRef.current) userMarkerRef.current.setLatLng(position);
    else userMarkerRef.current = L.marker(position, { icon: userIcon(), title: "You" }).addTo(map);
  }, [userLocation]);

  useEffect(() => {
    if (!recenterToken || !userLocation || !mapRef.current) return;
    mapRef.current.setView([userLocation.latitude, userLocation.longitude], 16);
  }, [recenterToken, userLocation]);

  return <div ref={containerRef} className="h-full w-full" aria-label="route map" />;
}
