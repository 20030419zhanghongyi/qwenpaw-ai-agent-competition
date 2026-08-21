/**
 * Story Discovery Catalog — every story the system knows about.
 *
 * Adding a new story in the future:
 * 1. Add a StoryCatalogEntry below.
 * 2. Set `status: "planned"` until its backend content package is ready.
 * 3. Flip to `status: "playable"` when the story is live.
 * 4. No code changes needed in the matcher — it reads the catalog.
 *
 * The matcher automatically ignores `status: "planned"` entries;
 * they only appear here to document the roadmap and to let the
 * catalog serve as the single source of truth for story metadata.
 */

import type { StoryCatalogEntry } from "./types";

export const STORY_CATALOG: StoryCatalogEntry[] = [
  // ── Playable ───────────────────────────────────────────────────────────
  {
    storyId: "lotus_city_double_map",
    status: "playable",
    title: "莲城双图：消失的界线",
    subtitle: "一场跨越约五百年的澳门时间层探索",
    region: "peninsula",
    estimatedHours: 7,
    invitationType: "telegram",
    matchRule: {
      durationAnyOf: ["full", "multi"],
      interestAnyOf: ["history", "culture", "arch"],
      themeAnyOf: ["heritage", "architecture"],
      minScore: 2,
    },
  },

  // ── Planned (not yet playable) ─────────────────────────────────────────
  {
    storyId: "taipa_letters",
    status: "planned",
    title: "氹仔家书",
    subtitle: "",
    region: "taipa",
    estimatedHours: 0,
    invitationType: "letter",
    matchRule: {
      durationAnyOf: [],
      interestAnyOf: [],
      themeAnyOf: [],
      minScore: 0,
    },
  },
  {
    storyId: "coloane_after_tide",
    status: "playable",
    title: "潮退之後",
    subtitle: "沿路環村、古廟、船廠與黑沙，補完一本潮汐工作簿",
    region: "coloane",
    estimatedHours: 4,
    invitationType: "audio_recording",
    matchRule: {
      durationAnyOf: ["half", "full"],
      interestAnyOf: ["history", "culture", "relax"],
      themeAnyOf: ["heritage", "leisure"],
      minScore: 1,
    },
  },
];
