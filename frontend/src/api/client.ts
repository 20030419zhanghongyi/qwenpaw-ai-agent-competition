import type { LanguageCode, POI, Preference, RouteMatchResponse } from "@/types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (method !== "GET" && method !== "HEAD" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail != null) {
        detail = JSON.stringify(body.detail);
      }
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export function matchRoutes(preference: Preference): Promise<RouteMatchResponse> {
  return request<RouteMatchResponse>("/api/v1/routes/match", {
    method: "POST",
    body: JSON.stringify(preference),
  });
}

export interface WalkSegment {
  from_poi_id: string;
  to_poi_id: string;
  walk_m: number;
  walk_min: number;
  polyline: string;
  bus_lines?: string[];
  modes?: Array<{ kind: string; label: string }>;
}

export interface WalkPathResponse {
  segments: WalkSegment[];
  total_walk_m: number;
  total_walk_min: number;
  polyline: string;
}

/** Dedupe StrictMode remounts for the same POI chain; never cache failures. */
const walkPathInflight = new Map<string, Promise<WalkPathResponse>>();

export function fetchWalkPath(poiIds: string[]): Promise<WalkPathResponse> {
  const key = poiIds.join("|");
  const existing = walkPathInflight.get(key);
  if (existing) return existing;

  const pending = request<WalkPathResponse>("/api/v1/routes/walk-path", {
    method: "POST",
    body: JSON.stringify({ poi_ids: poiIds }),
  }).then(
    (res) => {
      window.setTimeout(() => {
        if (walkPathInflight.get(key) === pending) walkPathInflight.delete(key);
      }, 30_000);
      return res;
    },
    (err) => {
      walkPathInflight.delete(key);
      throw err;
    },
  );
  walkPathInflight.set(key, pending);
  return pending;
}

export function listPois(
  params?: {
    q?: string;
    category?: string;
    limit?: number;
  },
  init?: RequestInit,
): Promise<POI[]> {
  const search = new URLSearchParams();
  if (params?.q) search.set("q", params.q);
  if (params?.category) search.set("category", params.category);
  if (params?.limit != null) search.set("limit", String(params.limit));
  const qs = search.toString();
  return request<POI[]>(`/api/v1/pois${qs ? `?${qs}` : ""}`, init);
}

export function parseIntent(text: string): Promise<{
  preference: Preference;
  source: "agent" | "rules" | string;
}> {
  return request("/api/v1/intent/parse", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export interface IntentGuideResponse {
  session_id: string;
  reply: string;
  ready: boolean;
  preference: Preference | null;
  source: "agent" | "script" | string;
  error?: string;
}

export function guideIntent(body: {
  action: "start" | "message";
  session_id?: string;
  message?: string;
  language: string;
  user_turn?: number;
  transcript?: string;
}): Promise<IntentGuideResponse> {
  return request("/api/v1/intent/guide", {
    method: "POST",
    body: JSON.stringify(body),
  });
}


export async function healthCheck(): Promise<{
  status: string;
  dashscope_configured?: boolean;
}> {
  return request("/api/v1/health");
}

export interface GuideTriggerResponse {
  triggered: boolean;
  reason?: string | null;
  poi?: POI & { distance_m?: number };
  distance_m?: number | null;
  prompt?: string | null;
  guide_request?: {
    poi: string;
    language: string;
    interests?: string[] | null;
  } | null;
}

export interface GuideGenerateResponse {
  text: string;
  source_type?: string;
  confidence?: number;
  ai_generated?: boolean;
  language?: string;
  source?: string;
  blocked?: boolean;
  error?: string | null;
  poi_name?: string;
}

export interface TTSResponse {
  audio_url: string;
  expires_in: number;
  content_type: string;
  language: string;
  voice: string;
}

export function triggerGuide(body: {
  longitude: number;
  latitude: number;
  session_id: string;
  radius_m?: number;
  language: string;
}): Promise<GuideTriggerResponse> {
  return request("/api/v1/guide/trigger", {
    method: "POST",
    body: JSON.stringify({
      radius_m: 80,
      ...body,
    }),
  });
}

export function generateGuide(body: {
  poi: string;
  language: string;
  interests?: string[];
  /** 下一站名称；空字符串表示末站；省略则无行程收尾语 */
  next_stop?: string | null;
}): Promise<GuideGenerateResponse> {
  return request("/api/v1/guide/generate", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export interface GuideAskResponse {
  poi_name: string;
  question: string;
  text: string;
  language?: string;
  source?: string;
  confidence?: number;
  ai_generated?: boolean;
  error?: string | null;
  web_used?: boolean;
  web_sources?: Array<{ title?: string; url?: string; source?: string }>;
}

export function askGuide(body: {
  poi: string;
  question: string;
  language: string;
  interests?: string[];
  web?: boolean;
}): Promise<GuideAskResponse> {
  const qs = body.web === false ? "?web=false" : "";
  return request(`/api/v1/guide/ask${qs}`, {
    method: "POST",
    body: JSON.stringify({
      poi: body.poi,
      question: body.question,
      language: body.language,
      interests: body.interests,
    }),
  });
}

export interface GuidePhotoResponse {
  description: string;
  candidate_poi?: string | null;
  confidence?: number;
  explanation?: { text?: string; source_type?: string } | null;
  recognition_status?: string;
  low_confidence_hint?: string | null;
  next_actions?: string[];
  error?: string | null;
  source?: string;
}

export async function recognizeGuidePhoto(args: {
  file: File;
  language: string;
}): Promise<GuidePhotoResponse> {
  const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
  const form = new FormData();
  form.append("file", args.file);
  const response = await fetch(
    `${API_BASE}/api/v1/guide/photo?language=${encodeURIComponent(args.language)}`,
    { method: "POST", body: form },
  );
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail != null) detail = JSON.stringify(body.detail);
    } catch {
      // keep
    }
    throw new Error(detail);
  }
  return response.json() as Promise<GuidePhotoResponse>;
}

export function synthesizeTts(body: {
  text: string;
  language: string;
}): Promise<TTSResponse> {
  return request("/api/v1/guide/tts", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export type { LanguageCode, Preference, POI, RouteMatchResponse };
