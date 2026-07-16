// Backend contracts used by the Web MVP. In development, Vite proxies /api.
const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export interface POI {
  poi_id: string;
  poi_name: string;
  alias?: string | null;
  address: string;
  longitude: number;
  latitude: number;
  category: string;
  source: string;
}

export interface RouteNode { poi_id: string; order: number; suggested_stay_min: number; note?: string; }
export interface Route {
  id: string; name: string; theme: string; duration_label: string; duration_hours: number;
  walk_distance_km: number; physical_level: string; suitable_for: string[]; nodes: RouteNode[]; description: string;
}
export interface MatchResult { route: Route; score: number; reasons: string[]; }
export interface Preference {
  duration: string; party_size?: number; travel_type?: string[]; interests?: string[];
  physical?: string[]; language: string;
}
export interface WalkSegment { from_poi_id: string; to_poi_id: string; walk_m: number; walk_min: number; polyline: string; }
export interface WalkPath { segments: WalkSegment[]; total_walk_m: number; total_walk_min: number; polyline: string; }
export interface GuideRequest { poi: string; language: string; interests?: string[]; }
export interface GuideTrigger {
  triggered: boolean; reason?: string; poi?: POI; distance_m?: number; prompt?: string; guide_request?: GuideRequest;
}
export interface GuideNarration { text: string; confidence: number; language: string; source: string; error?: string | null; }

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    const body = await res.json().catch(() => null) as { detail?: string } | null;
    throw new Error(body?.detail ?? `${res.status} ${path}`);
  }
  return res.json() as Promise<T>;
}

export const getHealth = () => api<{ status: string }>("/api/v1/health");
export const getPois = (q?: string) => api<POI[]>(`/api/v1/pois${q ? `?q=${encodeURIComponent(q)}` : ""}`);
export const matchRoutes = (pref: Preference) => api<{ preference: Preference; matches: MatchResult[] }>("/api/v1/routes/match", { method: "POST", body: JSON.stringify(pref) });
export const getWalkPath = (poi_ids: string[]) => api<WalkPath>("/api/v1/routes/walk-path", { method: "POST", body: JSON.stringify({ poi_ids }) });
export const triggerGuide = (longitude: number, latitude: number, session_id: string, language: string) => api<GuideTrigger>("/api/v1/guide/trigger", { method: "POST", body: JSON.stringify({ longitude, latitude, session_id, language }) });
export const generateGuide = (request: GuideRequest) => api<GuideNarration>("/api/v1/guide/generate", { method: "POST", body: JSON.stringify(request) });
