/**
 * Story Matcher — pure function that decides whether a user's preferences
 * qualify them for any playable story in the catalog.
 *
 * Design principles:
 *  - No side effects (no localStorage, no API calls).
 *  - Reads the catalog; only considers `status: "playable"` entries.
 *  - Hard eligibility gates (duration + cultural signal) are enforced BEFORE
 *    scoring so that a high score on one axis cannot paper over a missing gate.
 *  - Score is used for ranking between multiple eligible stories.
 *  - Returns a clean unmatched result when nothing qualifies.
 */

import type { StoryCatalogEntry, StoryDiscoveryPreference, StoryMatchResult } from "./types";
import { STORY_CATALOG } from "./storyCatalog";

// ── Helpers ────────────────────────────────────────────────────────────────

interface Eligibility {
  eligible: boolean;
  reasons: string[];
}

/**
 * Check hard eligibility gates for a single story.
 *
 * Gate 1 (duration):  if rule.durationAnyOf is non-empty the user's
 *   duration MUST appear in that list.
 *
 * Gate 2 (cultural signal):  if interestAnyOf or themeAnyOf is non-empty,
 *   the user must have at least one hit across the two pools:
 *     (interests ∩ interestAnyOf) ∪ (themes ∩ themeAnyOf) ≠ ∅
 */
function checkEligibility(
  pref: StoryDiscoveryPreference,
  rule: StoryCatalogEntry["matchRule"],
  storyId: string,
): Eligibility {
  const reasons: string[] = [];

  // Gate 1 — duration
  if (rule.durationAnyOf.length > 0) {
    if (!rule.durationAnyOf.includes(pref.duration)) {
      return {
        eligible: false,
        reasons: [
          `[${storyId}] duration gate FAILED: "${pref.duration}" ∉ [${rule.durationAnyOf.join(", ")}]`,
        ],
      };
    }
    reasons.push(
      `[${storyId}] duration gate passed: "${pref.duration}" ∈ [${rule.durationAnyOf.join(", ")}]`,
    );
  }

  // Gate 2 — cultural signal (interestAnyOf OR themeAnyOf)
  const hasCulturalReq = rule.interestAnyOf.length > 0 || rule.themeAnyOf.length > 0;
  if (hasCulturalReq) {
    const interestHits = pref.interests.filter((i) => rule.interestAnyOf.includes(i));
    const themeHits = pref.themes.filter((t) => rule.themeAnyOf.includes(t));

    if (interestHits.length === 0 && themeHits.length === 0) {
      const interestDetail =
        rule.interestAnyOf.length > 0
          ? `interests [${pref.interests.join(", ")}] ∩ [${rule.interestAnyOf.join(", ")}] = ∅`
          : "no interest requirement";
      const themeDetail =
        rule.themeAnyOf.length > 0
          ? `themes [${pref.themes.join(", ")}] ∩ [${rule.themeAnyOf.join(", ")}] = ∅`
          : "no theme requirement";
      return {
        eligible: false,
        reasons: [
          ...reasons,
          `[${storyId}] cultural-signal gate FAILED: ${interestDetail}; ${themeDetail}`,
        ],
      };
    }

    const parts: string[] = [];
    if (interestHits.length > 0) parts.push(`interests [${interestHits.join(", ")}]`);
    if (themeHits.length > 0) parts.push(`themes [${themeHits.join(", ")}]`);
    reasons.push(`[${storyId}] cultural-signal gate passed: ${parts.join(" + ")}`);
  }

  return { eligible: true, reasons };
}

interface Scoring {
  score: number;
  reasons: string[];
}

/** Walk tags that incur a -1 soft penalty. */
const WALK_PENALTY_TAGS = new Set(["less-walk", "accessible"]);

/**
 * Compute a score for ranking between eligible stories.
 *
 * Scoring model (P0):
 *   +1   duration is in durationAnyOf
 *   +1   per interest that matches interestAnyOf
 *   +1   per theme that matches themeAnyOf
 *   –1   if walkTags contains any penalty tag (soft signal, not a hard gate)
 */
function computeScore(
  pref: StoryDiscoveryPreference,
  rule: StoryCatalogEntry["matchRule"],
  storyId: string,
): Scoring {
  const reasons: string[] = [];
  let score = 0;

  // Duration contribution
  if (rule.durationAnyOf.length > 0 && rule.durationAnyOf.includes(pref.duration)) {
    score += 1;
    reasons.push(`[${storyId}] score +1 (duration "${pref.duration}")`);
  }

  // Interest hits
  const interestHits = pref.interests.filter((i) => rule.interestAnyOf.includes(i));
  if (interestHits.length > 0) {
    score += interestHits.length;
    reasons.push(`[${storyId}] score +${interestHits.length} (interests [${interestHits.join(", ")}])`);
  }

  // Theme hits
  const themeHits = pref.themes.filter((t) => rule.themeAnyOf.includes(t));
  if (themeHits.length > 0) {
    score += themeHits.length;
    reasons.push(`[${storyId}] score +${themeHits.length} (themes [${themeHits.join(", ")}])`);
  }

  // Walk penalty (soft)
  const penaltyTags = pref.walkTags.filter((t) => WALK_PENALTY_TAGS.has(t));
  if (penaltyTags.length > 0) {
    score -= 1;
    reasons.push(`[${storyId}] score -1 (walk penalty: [${penaltyTags.join(", ")}])`);
  }

  return { score, reasons };
}

// ── Sentinel ───────────────────────────────────────────────────────────────

const NO_MATCH: StoryMatchResult = Object.freeze({
  matched: false,
  storyId: "",
  score: 0,
  reasons: ["No eligible story found in catalog"],
  invitationType: "telegram" as const,
});

// ── Public API ─────────────────────────────────────────────────────────────

/**
 * Find the highest-scoring playable story that matches `pref`.
 *
 * Only `status: "playable"` catalog entries are considered.
 * Hard eligibility gates are enforced before scoring.
 *
 * @returns A StoryMatchResult — check `.matched` before using `.storyId`.
 */
export function matchStory(pref: StoryDiscoveryPreference): StoryMatchResult {
  const playableEntries = STORY_CATALOG.filter((e) => e.status === "playable");

  if (playableEntries.length === 0) {
    return { ...NO_MATCH, reasons: ["No playable stories in catalog"] };
  }

  let best: StoryMatchResult = { ...NO_MATCH };

  for (const entry of playableEntries) {
    // 1. Hard eligibility gates
    const eligibility = checkEligibility(pref, entry.matchRule, entry.storyId);
    if (!eligibility.eligible) {
      // Attach reasons even for ineligible stories to aid debugging.
      // In production you may strip these; for now they help trace "why not".
      continue;
    }

    // 2. Scoring
    const scoring = computeScore(pref, entry.matchRule, entry.storyId);

    // 3. Threshold check
    if (scoring.score < entry.matchRule.minScore) {
      continue;
    }

    // 4. Keep the highest-scoring result
    if (!best.matched || scoring.score > best.score) {
      best = {
        matched: true,
        storyId: entry.storyId,
        score: scoring.score,
        reasons: [...eligibility.reasons, ...scoring.reasons],
        invitationType: entry.invitationType,
      };
    }
  }

  return best;
}

// ── Inline test cases (manual verification) ────────────────────────────────
//
// These are NOT run by a test runner.  They serve as documentation and can be
// pasted into a REPL (browser console / Node) once the types are compiled away.
//
// --- Scenario 1: 历史兴趣（无需先填完整偏好）---
//   matchStory({ duration: "half", interests: ["history"], themes: [], walkTags: [] })
//   → { matched: true, storyId: "lotus_city_double_map", score: 1, ... }
//
// --- Scenario 2: 建筑爱好者 ---
//   matchStory({ duration: "multi", interests: ["arch"], themes: ["architecture"], walkTags: [] })
//   → { matched: true, storyId: "lotus_city_double_map", score: 2, ... }
//
// --- Scenario 3: 文化+摄影 ---
//   matchStory({ duration: "full", interests: ["culture", "photo"], themes: ["heritage"], walkTags: [] })
//   → { matched: true, storyId: "lotus_city_double_map", score: 2, ... }
//
// --- Scenario 4: 纯美食半日游 (half + food, no themes) ---
//   matchStory({ duration: "half", interests: ["food"], themes: [], walkTags: [] })
//   → { matched: false, ... }  (没有故事相关文化信号)
//
// --- Scenario 5: 夜间漫步 (night + heritage, no interests) ---
//   matchStory({ duration: "night", interests: [], themes: ["heritage"], walkTags: [] })
//   → { matched: true, storyId: "lotus_city_double_map", score: 1, ... }
//
// --- Scenario 6: 历史且少走路 ---
//   matchStory({ duration: "full", interests: ["history"], themes: ["heritage"], walkTags: ["less-walk"] })
//   → { matched: true, storyId: "lotus_city_double_map", score: 1, ... }
//
// --- Scenario 7: 路氹一日游 (full + cotai theme, no matching interests) ---
//   matchStory({ duration: "full", interests: [], themes: ["cotai"], walkTags: [] })
//   → { matched: false, ... }  (cultural-signal gate fails: cotai ∉ interestAnyOf ∪ themeAnyOf)
//
// --- Scenario 8: 空偏好 (all defaults) ---
//   matchStory({ duration: "half", interests: [], themes: [], walkTags: [] })
//   → { matched: false, ... }  (文化信号门槛未通过)
//
// --- Scenario 9: 单一文化兴趣与少走路 ---
//   matchStory({ duration: "full", interests: ["culture"], themes: [], walkTags: ["less-walk", "accessible"] })
//   → { matched: true, storyId: "lotus_city_double_map", score: 0, ... }
//
// --- Scenario 10: 双主题无兴趣 (full + heritage + architecture, no interests) ---
//   matchStory({ duration: "full", interests: [], themes: ["heritage", "architecture"], walkTags: [] })
//   → { matched: true, storyId: "lotus_city_double_map", score: 2, ... }
