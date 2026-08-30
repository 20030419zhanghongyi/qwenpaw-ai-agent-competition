import type { TripStatus } from "@/types/trips";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export interface HistoryTrip {
  trip_id: string;
  route_id: string;
  status: TripStatus;
  created_at: string;
  updated_at: string;
  total_stops: number;
  completed_stops: number;
  completion_ratio: number;
}

export interface FavoritePoi {
  user_id: string;
  poi_id: string;
  poi_name: string;
  created_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    credentials: "include",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function listTripHistory(userId: string): Promise<HistoryTrip[]> {
  return request(`/api/v1/users/${encodeURIComponent(userId)}/trips`);
}

export function listFavoritePois(userId: string): Promise<FavoritePoi[]> {
  return request(`/api/v1/users/${encodeURIComponent(userId)}/favorites/pois`);
}

export function removeFavoritePoi(userId: string, poiId: string): Promise<void> {
  return request(`/api/v1/users/${encodeURIComponent(userId)}/favorites/pois/${encodeURIComponent(poiId)}`, {
    method: "DELETE",
  });
}

export function submitTripFeedback(args: {
  tripId: string;
  userId: string;
  rating: number;
  comment?: string;
  routeReasonable?: boolean;
  walkingComfortable?: boolean;
}): Promise<unknown> {
  return request(`/api/v1/trips/${encodeURIComponent(args.tripId)}/feedback`, {
    method: "POST",
    body: JSON.stringify({
      user_id: args.userId,
      rating: args.rating,
      comment: args.comment || null,
      route_reasonable: args.routeReasonable ?? null,
      walking_comfortable: args.walkingComfortable ?? null,
    }),
  });
}
