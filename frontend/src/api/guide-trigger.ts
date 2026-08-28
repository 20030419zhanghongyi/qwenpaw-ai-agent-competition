import type { RoutePoi } from "@/types/routes";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export interface GuideTriggerResponse {
  triggered: boolean;
  reason?: string | null;
  poi?: RoutePoi & { distance_m?: number };
  distance_m?: number | null;
  prompt?: string | null;
  guide_request?: {
    poi: string;
    language: string;
    interests?: string[] | null;
  } | null;
}

export async function triggerGuide(body: {
  longitude: number;
  latitude: number;
  session_id: string;
  radius_m?: number;
  language: string;
}): Promise<GuideTriggerResponse> {
  const response = await fetch(`${API_BASE}/api/v1/guide/trigger`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ radius_m: 80, ...body }),
    credentials: "include",
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
      else if (payload.detail != null) detail = JSON.stringify(payload.detail);
    } catch {
      // Keep the HTTP status for non-JSON responses.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<GuideTriggerResponse>;
}
