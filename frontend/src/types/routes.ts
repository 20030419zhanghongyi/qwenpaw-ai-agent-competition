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
