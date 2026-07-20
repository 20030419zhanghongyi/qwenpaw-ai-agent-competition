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
  image_url: string;
  created_at: string;
}

export interface PostcardListResponse {
  postcards: Postcard[];
}
