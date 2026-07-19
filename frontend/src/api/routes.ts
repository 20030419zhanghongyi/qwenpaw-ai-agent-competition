import type {
  RouteAdjustmentRequest,
  RouteAdjustmentResult,
  RoutePoi,
  WalkPathResponse,
} from "@/types/routes";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (method !== "GET" && method !== "HEAD" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail != null) detail = JSON.stringify(body.detail);
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

const walkPathInflight = new Map<string, Promise<WalkPathResponse>>();

export function fetchRouteWalkPath(poiIds: string[]): Promise<WalkPathResponse> {
  const key = poiIds.join("|");
  const existing = walkPathInflight.get(key);
  if (existing) return existing;

  const pending = request<WalkPathResponse>("/api/v1/routes/walk-path", {
    method: "POST",
    body: JSON.stringify({ poi_ids: poiIds }),
  }).then(
    (result) => {
      window.setTimeout(() => {
        if (walkPathInflight.get(key) === pending) walkPathInflight.delete(key);
      }, 30_000);
      return result;
    },
    (error: unknown) => {
      walkPathInflight.delete(key);
      throw error;
    },
  );
  walkPathInflight.set(key, pending);
  return pending;
}

export async function fetchRoutePois(
  poiIds: string[],
  signal?: AbortSignal,
): Promise<RoutePoi[]> {
  const uniqueIds = [...new Set(poiIds.filter(Boolean))];
  if (uniqueIds.length === 0) return [];

  const rows = await request<RoutePoi[]>("/api/v1/pois?limit=500", { signal });
  const byId = new Map(rows.map((poi) => [poi.poi_id, poi]));
  const missing = uniqueIds.filter((poiId) => !byId.has(poiId));

  if (missing.length > 0) {
    const details = await Promise.all(
      missing.map((poiId) =>
        request<RoutePoi>(`/api/v1/pois/${encodeURIComponent(poiId)}`, { signal }),
      ),
    );
    for (const poi of details) byId.set(poi.poi_id, poi);
  }

  return uniqueIds.map((poiId) => byId.get(poiId)).filter((poi): poi is RoutePoi => Boolean(poi));
}

export function adjustRoute(
  adjustment: RouteAdjustmentRequest,
): Promise<RouteAdjustmentResult> {
  return request<RouteAdjustmentResult>("/api/v1/routes/adjust", {
    method: "POST",
    body: JSON.stringify(adjustment),
  });
}
