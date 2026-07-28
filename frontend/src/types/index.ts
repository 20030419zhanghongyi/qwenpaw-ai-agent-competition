/** Frontend API types aligned with backend Preference / route match contracts. */

export type LanguageCode = "zh-CN" | "zh-TW" | "en" | "pt";

export interface Preference {
  duration: "half-day" | "full-day" | "evening" | "multi-day" | "custom" | string;
  party_size: number;
  travel_type: string[];
  interests: string[];
  /** heritage / architecture / photo / food / family / leisure / cotai */
  themes: string[];
  physical: string[];
  language: string;
  /** Border-crossing poi_id for entry / exit anchors */
  entry_port?: string | null;
  exit_port?: string | null;
  /** YYYY-MM-DD for event / congestion estimates */
  travel_date?: string | null;
  /** Multi-day plan length (2–5); used as match top_k when duration is multi-day */
  trip_days?: number | null;
}

export interface RouteNode {
  poi_id: string;
  order: number;
  suggested_stay_min: number;
  note: string;
  replaceable_with: string[];
  /** Fixed border anchors from preference */
  anchor?: "entry" | "exit" | string;
}

export interface RouteTemplate {
  id: string;
  name: string;
  theme: string;
  duration_label: string;
  duration_hours: number;
  walk_distance_km: number;
  physical_level: string;
  suitable_for: string[];
  nodes: RouteNode[];
  description: string;
}

export interface MatchExplanation {
  summary?: string;
  details?: string[];
  [key: string]: unknown;
}

export interface MatchResult {
  route: RouteTemplate;
  score: number;
  reasons: string[];
  selected_template: string;
  candidate_pois: Array<Record<string, unknown>>;
  applied_constraints: string[];
  explanation: MatchExplanation;
  live_context?: {
    travel_date?: string;
    notes?: string[];
    weather?: Record<string, unknown>;
    events?: Record<string, unknown>;
    crowd_signal?: string;
  };
}

export interface RouteMatchResponse {
  preference: Preference;
  matches: MatchResult[];
}

export interface POI {
  poi_id: string;
  poi_name: string;
  alias: string | null;
  address: string;
  longitude: number;
  latitude: number;
  category: string;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface WalkSession {
  language: LanguageCode;
  preference: Preference;
  match: MatchResult;
  /** Multi-day plans keep several complementary matches (Day 1 / Day 2 / …). */
  matches?: MatchResult[];
  poisById: Record<string, POI>;
}
