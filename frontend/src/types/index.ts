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
}

export interface RouteNode {
  poi_id: string;
  order: number;
  suggested_stay_min: number;
  note: string;
  replaceable_with: string[];
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
