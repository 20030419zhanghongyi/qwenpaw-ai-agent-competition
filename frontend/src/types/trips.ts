export type TripStatus = "active" | "completed" | "cancelled";

export interface Trip {
  trip_id: string;
  user_id: string;
  route_id: string;
  status: TripStatus;
  stop_poi_ids: string[];
  checked_in_poi_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface TripProgress {
  total_stops: number;
  completed_stops: number;
  completion_ratio: number;
  next_poi_id: string | null;
}

export interface TripWithProgress {
  trip: Trip;
  progress: TripProgress;
}

export interface CreateTripInput {
  user_id: string;
  route_id: string;
}

export interface CheckInInput {
  poi_id: string;
}
