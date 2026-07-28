/**
 * Story Invitation State — lightweight per-story sessionStorage persistence.
 *
 * Design:
 *  - One key per account and story:
 *    macau-storywalk-invitation-{scope}-{storyId}
 *  - Stored shape:
 *    { scope, storyId, status: "accepted" | "declined", timestamp }
 *  - `not_seen` is the ABSENCE of a record — never written explicitly.
 *  - Both decisions suppress the card only for the same account in the current
 *    browser tab session. Logging out and switching accounts must not transfer
 *    the suppression decision.
 *
 * Robustness:
 *  - Every read is wrapped in try/catch — malformed JSON, unavailable
 *    sessionStorage (private browsing, storage full), and unexpected shapes
 *    all degrade to `not_seen`.
 *  - Writes silently no-op on failure — no global error UI.
 */

// ── Types ──────────────────────────────────────────────────────────────────

export type InvitationStatus = "not_seen" | "accepted" | "declined";

interface InvitationRecord {
  scope: string;
  storyId: string;
  status: "accepted" | "declined";
  timestamp: number;
}

// ── Internal helpers ───────────────────────────────────────────────────────

const KEY_PREFIX = "macau-storywalk-invitation-";

function normalizedScope(scope: string | null): string {
  const value = scope?.trim();
  return value ? `user-${encodeURIComponent(value)}` : "guest";
}

function storageKey(storyId: string, scope: string | null): string {
  return `${KEY_PREFIX}${normalizedScope(scope)}-${storyId}`;
}

/**
 * Read and validate a stored invitation record.
 *
 * Returns null for ANY of:
 *  - key does not exist
 *  - sessionStorage is unavailable (private browsing, sandboxed iframe, …)
 *  - JSON is malformed / not an object
 *  - stored storyId does not match the requested storyId
 *  - status is not one of the known values
 *  - timestamp is missing, non-finite, or ≤ 0
 */
function readRecord(
  storyId: string,
  scope: string | null,
): InvitationRecord | null {
  try {
    const expectedScope = normalizedScope(scope);
    const raw = sessionStorage.getItem(storageKey(storyId, scope));
    if (raw === null) return null;

    const parsed: unknown = JSON.parse(raw);

    if (!parsed || typeof parsed !== "object") return null;

    const record = parsed as Record<string, unknown>;

    if (record.scope !== expectedScope) return null;

    // Validate storyId
    if (typeof record.storyId !== "string" || record.storyId !== storyId) {
      return null;
    }

    // Validate status
    if (record.status !== "accepted" && record.status !== "declined") {
      return null;
    }

    // Validate timestamp
    if (typeof record.timestamp !== "number" || !Number.isFinite(record.timestamp) || record.timestamp <= 0) {
      return null;
    }

    return {
      scope: expectedScope,
      storyId: record.storyId,
      status: record.status,
      timestamp: record.timestamp,
    };
  } catch {
    // sessionStorage throw, JSON parse error, or any unexpected path
    return null;
  }
}

/** Write a record.  Silently no-op on any failure. */
function writeRecord(record: InvitationRecord): void {
  try {
    sessionStorage.setItem(
      `${KEY_PREFIX}${record.scope}-${record.storyId}`,
      JSON.stringify(record),
    );
  } catch {
    // quota exceeded, storage unavailable, or write denied
  }
}

/** Remove the stored record for a story.  Silently no-op on failure. */
function removeRecord(storyId: string, scope: string | null): void {
  try {
    sessionStorage.removeItem(storageKey(storyId, scope));
  } catch {
    // storage unavailable
  }
}

// ── Public API ─────────────────────────────────────────────────────────────

/**
 * Return the current invitation status for a story.
 *
 *  - No stored record                          → "not_seen"
 *  - Stored "accepted"                         → "accepted"
 *  - Stored "declined"                         → "declined"
 *  - Any storage error / malformed data        → "not_seen"
 */
export function getInvitationStatus(
  storyId: string,
  scope: string | null,
): InvitationStatus {
  const record = readRecord(storyId, scope);
  if (!record) return "not_seen";

  return record.status;
}

/**
 * Mark a story invitation as accepted.
 *
 * The user will not see the invitation card again in this tab session.
 */
export function markInvitationAccepted(
  storyId: string,
  scope: string | null,
): void {
  writeRecord({
    scope: normalizedScope(scope),
    storyId,
    status: "accepted",
    timestamp: Date.now(),
  });
}

/**
 * Mark a story invitation as declined.
 *
 * The decline is honoured for the current tab session.
 */
export function markInvitationDeclined(
  storyId: string,
  scope: string | null,
): void {
  writeRecord({
    scope: normalizedScope(scope),
    storyId,
    status: "declined",
    timestamp: Date.now(),
  });
}

/**
 * Remove all invitation state for a story.
 *
 * After this call getInvitationStatus() returns "not_seen" and
 * hasActiveInvitationSuppression() returns false — as if the user
 * had never seen the invitation.
 */
export function clearInvitationState(
  storyId: string,
  scope: string | null,
): void {
  removeRecord(storyId, scope);
}

/**
 * Carry a guest decision into the account created or signed in from the same
 * invitation flow. The guest keys are removed after a successful transfer.
 */
export function adoptGuestInvitationState(userId: string): void {
  try {
    const guestPrefix = `${KEY_PREFIX}guest-`;
    const guestKeys: string[] = [];
    for (let index = 0; index < sessionStorage.length; index += 1) {
      const key = sessionStorage.key(index);
      if (key?.startsWith(guestPrefix)) guestKeys.push(key);
    }

    for (const key of guestKeys) {
      const raw = sessionStorage.getItem(key);
      if (!raw) continue;
      const parsed = JSON.parse(raw) as Partial<InvitationRecord>;
      if (
        parsed.scope !== "guest" ||
        typeof parsed.storyId !== "string" ||
        (parsed.status !== "accepted" && parsed.status !== "declined") ||
        typeof parsed.timestamp !== "number" ||
        !Number.isFinite(parsed.timestamp)
      ) {
        continue;
      }
      writeRecord({
        scope: normalizedScope(userId),
        storyId: parsed.storyId,
        status: parsed.status,
        timestamp: parsed.timestamp,
      });
    }

    for (const key of guestKeys) sessionStorage.removeItem(key);
  } catch {
    // Storage failures degrade to showing the invitation again.
  }
}

/** End the invitation session when the current account signs out. */
export function clearInvitationSession(): void {
  try {
    const keys: string[] = [];
    for (let index = 0; index < sessionStorage.length; index += 1) {
      const key = sessionStorage.key(index);
      if (key?.startsWith(KEY_PREFIX)) keys.push(key);
    }
    for (const key of keys) sessionStorage.removeItem(key);
  } catch {
    // Storage may be unavailable in private or restricted browsing modes.
  }
}

/**
 * Whether any active suppression is in effect for this story.
 *
 * Returns true when:
 *  - accepted in the current tab session
 *  - declined in the current tab session
 *
 * Returns false when:
 *  - not_seen (no record, or expired declined, or storage error)
 *
 * This is a convenience wrapper so callers don't need to reason about
 * the individual status values.
 */
export function hasActiveInvitationSuppression(
  storyId: string,
  scope: string | null,
): boolean {
  const status = getInvitationStatus(storyId, scope);
  return status === "accepted" || status === "declined";
}
