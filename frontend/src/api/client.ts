// 后端 API 客户端。
// 本地开发走 vite proxy（VITE_API_BASE_URL 留空 → 相对路径 /api）。
// 部署到其他域名时在 .env 设置 VITE_API_BASE_URL=https://api.example.com

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export interface POI {
  id: string;
  name_zh: string;
  name_en?: string;
  name_pt?: string;
  district: string;
  theme: string[];
  coordinates: { lat: number; lng: number };
  intro: string;
  history: string;
  architecture: string;
  story: string;
  observation_tips: string;
  suitable_for: string[];
  source_type: string;
}

export interface RouteNode {
  poi_id: string;
  order: number;
  suggested_stay_min: number;
  note?: string;
  replaceable_with?: string[];
}

export interface Route {
  id: string;
  name: string;
  theme: string;
  duration_label: string;
  duration_hours: number;
  walk_distance_km: number;
  physical_level: string;
  suitable_for: string[];
  nodes: RouteNode[];
  description: string;
}

export interface MatchResult {
  route: Route;
  score: number;
  reasons: string[];
}

export interface Preference {
  duration: string;
  party_size?: number;
  travel_type?: string[];
  interests?: string[];
  physical?: string[];
  language: string;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json() as Promise<T>;
}

export const getHealth = () => api<{ status: string }>("/api/v1/health");
export const getPois = () => api<POI[]>("/api/v1/pois");
export const getRoutes = () => api<Route[]>("/api/v1/routes");
export const matchRoutes = (pref: Preference) =>
  api<{ preference: Preference; matches: MatchResult[] }>(
    "/api/v1/routes/match",
    { method: "POST", body: JSON.stringify(pref) },
  );
