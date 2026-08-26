/** Stable guest id so trip/postcard APIs work without login. */

const GUEST_KEY = "macau-storywalk-guest-id";

export function readGuestUserId(): string | null {
  try {
    return localStorage.getItem(GUEST_KEY);
  } catch {
    return null;
  }
}

export function clearGuestUserId(): void {
  try {
    localStorage.removeItem(GUEST_KEY);
  } catch {
    // A failed cleanup is harmless; claiming guest trips is idempotent.
  }
}

export function getOrCreateGuestUserId(): string {
  try {
    const existing = readGuestUserId();
    if (existing) return existing;
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? `guest-${crypto.randomUUID()}`
        : `guest-${Date.now().toString(36)}`;
    localStorage.setItem(GUEST_KEY, id);
    return id;
  } catch {
    return "guest-session";
  }
}

/** Prefer authenticated user; otherwise a persisted guest id. */
export function resolveTripUserId(authUserId: string | null | undefined): string {
  if (authUserId) return authUserId;
  return getOrCreateGuestUserId();
}
