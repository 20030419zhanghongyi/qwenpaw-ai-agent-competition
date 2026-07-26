/**
 * Story Invitation State — lightweight per-story localStorage persistence.
 *
 * Design:
 *  - One key per story:  macau-storywalk-invitation-{storyId}
 *  - Stored shape:       { storyId, status: "accepted" | "declined", timestamp }
 *  - `not_seen` is the ABSENCE of a record — never written explicitly.
 *  - `accepted` persists forever (user made an explicit positive choice).
 *  - `declined` has a cooldown (INVITATION_DECLINE_COOLDOWN_DAYS); after it
 *    expires the stale record is cleaned up and the status reverts to not_seen.
 *
 * Robustness:
 *  - Every read is wrapped in try/catch — malformed JSON, unavailable
 *    localStorage (private browsing, storage full), and unexpected shapes
 *    all degrade to `not_seen`.
 *  - Writes silently no-op on failure — no global error UI.
 */

import { INVITATION_DECLINE_COOLDOWN_DAYS } from "./types";

// ── Types ──────────────────────────────────────────────────────────────────

export type InvitationStatus = "not_seen" | "accepted" | "declined";

interface InvitationRecord {
  storyId: string;
  status: "accepted" | "declined";
  timestamp: number;
}

// ── Internal helpers ───────────────────────────────────────────────────────

const KEY_PREFIX = "macau-storywalk-invitation-";

function storageKey(storyId: string): string {
  return `${KEY_PREFIX}${storyId}`;
}

/**
 * Read and validate a stored invitation record.
 *
 * Returns null for ANY of:
 *  - key does not exist
 *  - localStorage is unavailable (private browsing, sandboxed iframe, …)
 *  - JSON is malformed / not an object
 *  - stored storyId does not match the requested storyId
 *  - status is not one of the known values
 *  - timestamp is missing, non-finite, or ≤ 0
 */
function readRecord(storyId: string): InvitationRecord | null {
  try {
    const raw = localStorage.getItem(storageKey(storyId));
    if (raw === null) return null;

    const parsed: unknown = JSON.parse(raw);

    if (!parsed || typeof parsed !== "object") return null;

    const record = parsed as Record<string, unknown>;

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
      storyId: record.storyId,
      status: record.status,
      timestamp: record.timestamp,
    };
  } catch {
    // localStorage throw, JSON parse error, or any unexpected path
    return null;
  }
}

/** Write a record.  Silently no-op on any failure. */
function writeRecord(record: InvitationRecord): void {
  try {
    localStorage.setItem(storageKey(record.storyId), JSON.stringify(record));
  } catch {
    // quota exceeded, storage unavailable, or write denied
  }
}

/** Remove the stored record for a story.  Silently no-op on failure. */
function removeRecord(storyId: string): void {
  try {
    localStorage.removeItem(storageKey(storyId));
  } catch {
    // storage unavailable
  }
}

/** Cooldown duration in milliseconds. */
function cooldownMs(): number {
  return INVITATION_DECLINE_COOLDOWN_DAYS * 24 * 60 * 60 * 1000;
}

// ── Public API ─────────────────────────────────────────────────────────────

/**
 * Return the current invitation status for a story.
 *
 *  - No stored record                          → "not_seen"
 *  - Stored "accepted"                         → "accepted" (forever)
 *  - Stored "declined" within cooldown         → "declined"
 *  - Stored "declined" past cooldown           → "not_seen" (stale record removed)
 *  - Any storage error / malformed data        → "not_seen"
 */
export function getInvitationStatus(storyId: string): InvitationStatus {
  const record = readRecord(storyId);
  if (!record) return "not_seen";

  // Accepted is permanent — no expiry.
  if (record.status === "accepted") return "accepted";

  // Declined — check cooldown window.
  if (record.status === "declined") {
    const elapsed = Date.now() - record.timestamp;
    if (elapsed >= cooldownMs()) {
      // Cooldown expired — clean up and treat as fresh.
      removeRecord(storyId);
      return "not_seen";
    }
    return "declined";
  }

  // Should be unreachable (validated in readRecord), but be defensive.
  return "not_seen";
}

/**
 * Mark a story invitation as accepted.
 *
 * This persists permanently — the user will not see the automatic
 * first-invitation cutscene again for this story.
 */
export function markInvitationAccepted(storyId: string): void {
  writeRecord({
    storyId,
    status: "accepted",
    timestamp: Date.now(),
  });
}

/**
 * Mark a story invitation as declined.
 *
 * The decline is honoured for INVITATION_DECLINE_COOLDOWN_DAYS; after that
 * getInvitationStatus() automatically treats it as not_seen.
 */
export function markInvitationDeclined(storyId: string): void {
  writeRecord({
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
export function clearInvitationState(storyId: string): void {
  removeRecord(storyId);
}

/**
 * Whether any active suppression is in effect for this story.
 *
 * Returns true when:
 *  - accepted (permanent)
 *  - declined (still within the cooldown window)
 *
 * Returns false when:
 *  - not_seen (no record, or expired declined, or storage error)
 *
 * This is a convenience wrapper so callers don't need to reason about
 * the individual status values.
 */
export function hasActiveInvitationSuppression(storyId: string): boolean {
  const status = getInvitationStatus(storyId);
  return status === "accepted" || status === "declined";
}
