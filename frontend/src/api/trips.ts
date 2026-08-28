import type {
  CheckInInput,
  CreateTripInput,
  LocationCheckInInput,
  TripProgress,
  TripWithProgress,
} from "@/types/trips";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class TripApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "TripApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (method !== "GET" && method !== "HEAD" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail != null) detail = JSON.stringify(body.detail);
    } catch {
      // Keep the HTTP status text when the response is not JSON.
    }
    throw new TripApiError(detail, response.status);
  }

  return response.json() as Promise<T>;
}

export function createTrip(input: CreateTripInput): Promise<TripWithProgress> {
  return request("/api/v1/trips", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getTrip(tripId: string): Promise<TripWithProgress> {
  return request(`/api/v1/trips/${encodeURIComponent(tripId)}`);
}

export function getCurrentTrip(userId: string): Promise<TripWithProgress> {
  return request(`/api/v1/users/${encodeURIComponent(userId)}/current-trip`);
}

export function checkInTrip(
  tripId: string,
  input: CheckInInput,
): Promise<TripWithProgress> {
  return request(`/api/v1/trips/${encodeURIComponent(tripId)}/checkins`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function checkInTripAtLocation(
  tripId: string,
  input: LocationCheckInInput,
): Promise<TripWithProgress> {
  return request(`/api/v1/trips/${encodeURIComponent(tripId)}/location-checkins`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getTripProgress(tripId: string): Promise<TripProgress> {
  return request(`/api/v1/trips/${encodeURIComponent(tripId)}/progress`);
}
