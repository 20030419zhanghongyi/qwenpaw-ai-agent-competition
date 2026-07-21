/** Frontend types aligned with backend postcard contracts. */

export interface Postcard {
  postcard_id: string;
  trip_id: string;
  poi_id: string;
  poi_name: string;
  stop_order: number;
  caption: string;
  caption_source: string;
  source_type: string;
  ai_generated: boolean;
  language: string;
  review_decision: string;
  photo_scrubbed: boolean;
  has_user_photo?: boolean;
  scene_source?: "user" | "ai" | "library" | "placeholder" | string;
  image_url: string;
  created_at: string;
  visited_at?: string | null;
  timestamp_label?: string;
  geo_label?: string;
  latitude?: number | null;
  longitude?: number | null;
  district?: string | null;
  route_id?: string | null;
  route_name?: string | null;
  task_label?: string;
}

export interface PostcardListResponse {
  postcards: Postcard[];
}
