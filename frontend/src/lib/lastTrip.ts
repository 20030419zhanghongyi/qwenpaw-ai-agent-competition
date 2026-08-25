const LAST_TRIP_KEY = "macau-storywalk-last-trip-id";

export function rememberLastTripId(tripId: string | null | undefined): void {
  const value = tripId?.trim();
  if (!value) return;
  try {
    localStorage.setItem(LAST_TRIP_KEY, value);
  } catch {
    // Storage can be unavailable in private browsing; the in-memory trip still works.
  }
}

export function getLastTripId(): string | null {
  try {
    return localStorage.getItem(LAST_TRIP_KEY)?.trim() || null;
  } catch {
    return null;
  }
}
