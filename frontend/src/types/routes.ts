import type { MatchExplanation, Preference, RouteNode, RouteTemplate } from "@/types";

export interface RoutePoi {
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

export interface TransitMode {
  kind: string;
  label: string;
}

export interface WalkSegment {
  from_poi_id: string;
  to_poi_id: string;
  walk_m: number;
  walk_min: number;
  polyline: string;
  bus_lines?: string[];
  modes?: TransitMode[];
}

export interface WalkPathResponse {
  segments: WalkSegment[];
  total_walk_m: number;
  total_walk_min: number;
  polyline: string;
}

export interface RouteAdjustmentRequest {
  route_id: string;
  instruction: string;
  preference: Preference;
}

export type RouteNodeChange = RouteNode & {
  poi_name?: string;
  previous_order?: number;
  new_order?: number;
};

export interface RouteAdjustmentResult {
  selected_template: string;
  instruction: string;
  preference_before: Preference;
  preference_after: Preference;
  route: RouteTemplate;
  candidate_pois: Array<Record<string, unknown>>;
  removed_nodes: RouteNodeChange[];
  added_nodes: RouteNodeChange[];
  reordered_nodes: RouteNodeChange[];
  rationale: string[];
  applied_constraints: string[];
  explanation: MatchExplanation;
  source: "agent" | "rules" | string;
}
