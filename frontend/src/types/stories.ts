/** TypeScript types derived from the Story backend models. */

/* ── Story overview (GET /api/v1/stories/{storyId}) ── */

export interface StoryNodeOverview {
  id: string;
  order: number;
  kind: string;
  title: string;
  story_time?: string;
  poi_id?: string;
}

export interface StoryEndingOverview {
  id: string;
  title: string;
  choice_text: string;
}

export interface StoryOverview {
  id: string;
  version: number;
  title: string;
  subtitle: string;
  summary: string;
  route_id: string;
  estimated_hours: number;
  presentation?: {
    default_orientation?: string;
    max_content_width_px?: number;
    cover_asset_id?: string;
    asset_base_path?: string;
  };
  identity?: StoryIdentity;
  content_notice?: string;
  content_labels?: Record<string, string>;
  characters?: StoryCharacter[];
  nodes: StoryNodeOverview[];
  endings: StoryEndingOverview[];
}

export interface StoryIdentity {
  id: string;
  name: string;
  description: string;
}

export interface StoryCharacter {
  id: string;
  name: string;
  role: string;
  fictional: boolean;
}

/* ── Session state ── */

export type StorySessionStatus = "active" | "completed";

export type StoryAction =
  | "arrive"
  | "answer"
  | "hint"
  | "skip"
  | "continue"
  | "choose_ending";

export interface StoryReward {
  id: string;
  kind: string;
  name?: string | null;
  text?: string | null;
}

export interface StorySessionState {
  arrived_chapter_ids: string[];
  completed_chapter_ids: string[];
  hinted_chapter_ids: string[];
  skipped_chapter_ids: string[];
  clues: string[];
  rewards: StoryReward[];
  choices: Record<string, string>;
  attempts: Record<string, number>;
  hint_counts: Record<string, number>;
  ending_id: string | null;
  ending_reflection: string | null;
}

export interface StoryProgressResponse {
  total_chapters: number;
  completed_chapters: number;
  total_puzzles: number;
  solved_puzzles: number;
  hinted_puzzles: number;
  skipped_puzzles: number;
}

/* ── Story chapter content (current_chapter in session response) ── */

export interface TimeLayer {
  period: string;
  focus: string;
}

export interface StoryKnowledgeCard {
  kind: string;
  title: string;
  text: string;
}

export interface PuzzleOption {
  id: string;
  text: string;
}

export interface StoryPuzzle {
  id: string;
  type: string;
  prompt: string;
  fields?: Array<{ id: string; label: string }>;
  options?: PuzzleOption[];
  required_count?: number;
  hints?: string[];
  explanation?: string;
  skip_text?: string;
  reward?: StoryReward;
}

export interface StoryFallback {
  type: string;
  text: string;
}

export interface StoryEndingOption {
  id: string;
  title: string;
  choice_text: string;
  text?: string;
}

export interface StoryChapter {
  id: string;
  order: number;
  kind: string;
  title: string;
  location_name?: string;
  story_time?: string;
  poi_id?: string;
  secondary_poi_ids?: string[];
  scene?: string;
  pages?: StoryPage[];
  dialogue?: Array<{ speaker: string; text: string }>;
  time_layers?: TimeLayer[];
  knowledge_cards?: StoryKnowledgeCard[];
  fallback?: StoryFallback;
  puzzle?: StoryPuzzle;
  reward?: StoryReward;
  poi_status?: string;
  ending_options?: StoryEndingOverview[];
}

export interface StoryPage {
  id: string;
  kind?: string;
  title?: string;
  text?: string;
  speaker?: string;
  asset_id?: string;
}

/* ── Session responses ── */

export interface StorySessionResponse {
  session_id: string;
  user_id: string;
  story_id: string;
  trip_id: string;
  current_chapter_id: string;
  status: StorySessionStatus;
  state: StorySessionState;
  current_chapter: StoryChapter | null;
  ending: StoryEndingOption | null;
  allowed_actions: StoryAction[];
  progress: StoryProgressResponse;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

/* ── Action request / response ── */

export interface StoryActionRequest {
  action: StoryAction;
  chapter_id: string;
  answer?: unknown;
  choice_id?: string;
  reflection?: string;
}

export interface StoryActionResponse {
  accepted: boolean;
  message: string;
  hint?: string | null;
  new_clues: string[];
  new_rewards: StoryReward[];
  session: StorySessionResponse;
}
