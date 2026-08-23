/**
 * Story Discovery — minimal types shared by catalog, matcher, and invitation.
 *
 * These types are intentionally decoupled from the rest of the frontend
 * (no imports from @/types, @/lib/preference, etc.) so the matching layer
 * stays self-contained and easy to unit-test.
 */

// ── Enums ──────────────────────────────────────────────────────────────────

/** How the story is presented to the user in the cutscene. */
export type InvitationType = "telegram" | "letter" | "audio_recording";

/** Whether a story is ready for matching. */
export type StoryStatus = "playable" | "planned";

// ── Preference (matching input) ────────────────────────────────────────────

/**
 * Minimal preference subset that the Story Matcher actually needs.
 *
 * Later, PreferencePage will map its existing PreferenceFormState into this
 * shape before calling matchStory().  The fields mirror the UI-level ids
 * used in the preference form:
 *  - duration: "half" | "full" | "night" | "multi"
 *  - interests: "history" | "culture" | "arch" | "food" | "photo" | "relax"
 *  - themes:   "heritage" | "architecture" | "photo" | "food" | "family" | "leisure" | "cotai"
 *  - walkTags: "less-walk" | "no-backtrack" | "shade" | "flat" | "indoor" | "accessible"
 */
export interface StoryDiscoveryPreference {
  /** UI-level duration id (e.g. "half" | "full" | "night" | "multi"). */
  duration: string;
  /** Selected interest ids. */
  interests: string[];
  /** Selected theme ids. */
  themes: string[];
  /** Selected walking constraint tags. */
  walkTags: string[];
}

// ── Match rule (catalog authoring) ─────────────────────────────────────────

/**
 * Eligibility + scoring rule authored per story in the catalog.
 *
 * Naming uses `*AnyOf` to make OR semantics explicit:
 *  - `durationAnyOf`  — the user's duration MUST be one of these (hard gate).
 *  - `interestAnyOf`  — at least ONE of these interests must be present (hard gate
 *    when non-empty; pooled with themeAnyOf).
 *  - `themeAnyOf`     — at least ONE of these themes must be present (hard gate
 *    when non-empty; pooled with interestAnyOf).
 *
 * The cultural-signal gate passes when there is at least one hit across
 * (interests ∩ interestAnyOf) ∪ (themes ∩ themeAnyOf).  If both lists are
 * empty the gate is skipped (anyone may match on duration alone).
 */
export interface StoryMatchRule {
  /** Duration id(s) the user MUST have.  Empty = no duration gate. */
  durationAnyOf: string[];
  /** Interest pool for the cultural-signal OR gate.  Empty = skip. */
  interestAnyOf: string[];
  /** Theme pool for the cultural-signal OR gate.  Empty = skip. */
  themeAnyOf: string[];
  /** Score must be ≥ this value after scoring to be considered matched. */
  minScore: number;
}

// ── Catalog entry ──────────────────────────────────────────────────────────

/** One story in the discovery catalog. */
export interface StoryCatalogEntry {
  storyId: string;
  status: StoryStatus;
  title: string;
  subtitle: string;
  /** Macau region: "peninsula" | "taipa" | "coloane". */
  region: string;
  /** Estimated play time in hours. */
  estimatedHours: number;
  invitationType: InvitationType;
  matchRule: StoryMatchRule;
}

// ── Matcher output ─────────────────────────────────────────────────────────

/** Result of running matchStory() against the catalog. */
export interface StoryMatchResult {
  /** Whether an eligible story with score ≥ minScore was found. */
  matched: boolean;
  /** The matched story id (empty string when unmatched). */
  storyId: string;
  /** Computed score (0 when unmatched). */
  score: number;
  /** Human-readable reasons describing eligibility gates and score breakdown. */
  reasons: string[];
  /** Which cutscene style to use (telegram when unmatched — unused). */
  invitationType: InvitationType;
}
