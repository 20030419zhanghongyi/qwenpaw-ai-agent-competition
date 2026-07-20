/** Stable guest id so trip/postcard APIs work without login. */

const GUEST_KEY = "macau-storywalk-guest-id";

export function getOrCreateGuestUserId(): string {
  try {
    const existing = localStorage.getItem(GUEST_KEY);
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
