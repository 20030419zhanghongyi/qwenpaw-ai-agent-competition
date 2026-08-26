/** Public TypeScript contracts exposed by the Story V4 backend. */

/* ── Shared content primitives ── */

export type StoryNodeKind =
  | "prologue"
  | "narrative"
  | "transition"
  | "puzzle"
  | "ending";

export type StorySpeakerId = "player" | "alian" | "alan" | "m";

export type StoryKnowledgeKind =
  | "historical_fact"
  | "folklore"
  | "contextual_reconstruction"
  | "fictional_story"
  | "dynamic_operational_info";

export type StoryKnowledgeConfidence = "high" | "medium" | "low";

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

export interface StoryAssetRef {
  asset_id: string;
  alt: string;
  caption: string;
}

export interface StoryDialogueLine {
  id: string;
  speaker_id: StorySpeakerId;
  speaker: string;
  text: string;
  portrait_asset_id?: string;
}

export interface StoryKnowledgeCard {
  kind: StoryKnowledgeKind;
  title: string;
  text: string;
  source_label: string;
  confidence: StoryKnowledgeConfidence;
}

export interface StoryAgentContext {
  persona: string;
  poi_name: string;
  chapter_goal: string;
  known_facts: string[];
  fiction_boundaries: string[];
  suggested_questions: string[];
  do_not_reveal: string[];
}

export interface StoryNodePresentation {
  layout: string;
  assets: string[];
}

export interface StoryPresentation {
  default_orientation: string;
  max_content_width_px: number;
  cover_asset_id: string;
  asset_base_path: string;
}

export interface StoryFallback {
  type: string;
  text: string;
}

export interface StoryReward {
  id: string;
  kind: string;
  name: string | null;
  text: string | null;
}

/* ── Story overview (GET /api/v1/stories/{storyId}) ── */

export interface StoryNodeOverview {
  id: string;
  order: number;
  kind: StoryNodeKind;
  title: string;
  story_time?: string;
  location_name?: string;
  poi_id?: string;
}

export interface StoryEndingOverview {
  id: string;
  title: string;
  choice_text: string;
}

/** Shape consumed while an ending may still be only a public summary. */
export interface StoryEndingOption extends StoryEndingOverview {
  text?: string;
  rewards?: StoryReward[];
}

export interface StoryEnding extends StoryEndingOption {
  text: string;
  rewards: StoryReward[];
}

export interface StoryOverview {
  id: string;
  version: number;
  title: string;
  subtitle: string;
  summary: string;
  route_id: string;
  estimated_hours: number;
  product_mode: string;
  presentation: StoryPresentation;
  identity: StoryIdentity;
  content_notice: string;
  content_labels: Record<StoryKnowledgeKind, string>;
  characters: StoryCharacter[];
  props: string[];
  nodes: StoryNodeOverview[];
  endings: StoryEndingOverview[];
}

/* ── Public puzzle content (solution is intentionally absent) ── */

export interface PuzzleOption {
  id: string;
  text: string;
  description?: string;
  source_label?: string;
  asset_id?: string;
}

export interface MappingPuzzleField {
  id: string;
  label: string;
}

interface StoryPuzzleBase {
  id: string;
  prompt: string;
  options: PuzzleOption[];
  /**
   * The backend currently sends the authored hint list in current_chapter.
   * UI code must still reveal hints only from StoryActionResponse.hint.
   */
  hints: string[];
  explanation: string;
  skip_text: string;
  reward: StoryReward;
}

export interface MultiSelectPuzzle extends StoryPuzzleBase {
  type: "multi_select";
}

export interface MappingPuzzle extends StoryPuzzleBase {
  type: "mapping";
  fields: MappingPuzzleField[];
}

export interface EvidenceChainPuzzle extends StoryPuzzleBase {
  type: "evidence_chain";
  required_count?: number;
}

export interface AssemblyPuzzle extends StoryPuzzleBase {
  type: "assembly";
}

/**
 * Compatibility shape for pre-V4 story packages. V4 pages should narrow to
 * V4StoryPuzzle and never infer an answer from this type.
 */
export interface SingleChoicePuzzle extends StoryPuzzleBase {
  type: "single_choice";
}

export type V4StoryPuzzle =
  | MultiSelectPuzzle
  | MappingPuzzle
  | EvidenceChainPuzzle
  | AssemblyPuzzle;

export type StoryPuzzle = V4StoryPuzzle | SingleChoicePuzzle;

/* ── Current chapter in a session response ── */

/** Compatibility-only fields retained while legacy story pages are replaced. */
export interface TimeLayer {
  period: string;
  focus: string;
}

interface StoryChapterBase {
  id: string;
  order: number;
  kind: StoryNodeKind;
  title: string;
  story_time?: string;
  location_name?: string;
  poi_id?: string;
  scene?: string;
  arrival_comic?: StoryAssetRef[];
  dialogue?: StoryDialogueLine[];
  knowledge_cards?: StoryKnowledgeCard[];
  agent_context?: StoryAgentContext;
  presentation?: StoryNodePresentation;
  fallback?: StoryFallback;
  reward?: StoryReward;
  ending_options?: StoryEndingOverview[];
  puzzle?: StoryPuzzle;

  // Legacy response compatibility; not populated by the frozen V4 package.
  secondary_poi_ids?: string[];
  time_layers?: TimeLayer[];
  poi_status?: string;
}

export interface StoryPrologueChapter extends StoryChapterBase {
  kind: "prologue";
  puzzle?: never;
}

export interface StoryNarrativeChapter extends StoryChapterBase {
  kind: "narrative" | "transition";
  puzzle?: never;
}

export interface StoryPuzzleChapter extends StoryChapterBase {
  kind: "puzzle";
  poi_id: string;
  location_name: string;
  puzzle: StoryPuzzle;
}

export interface StoryEndingChapter extends StoryChapterBase {
  kind: "ending";
  poi_id: string;
  location_name: string;
  puzzle?: never;
  ending_options?: StoryEndingOverview[];
}

export type StoryChapter =
  | StoryPrologueChapter
  | StoryNarrativeChapter
  | StoryPuzzleChapter
  | StoryEndingChapter;

/* ── Session state and responses ── */

export type StorySessionStatus = "active" | "completed";

export type StoryAction =
  | "arrive"
  | "answer"
  | "hint"
  | "skip"
  | "continue"
  | "choose_ending";

export interface StorySessionState {
  content_version: number;
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

export interface StorySessionResponse {
  session_id: string;
  user_id: string;
  story_id: string;
  trip_id: string;
  current_chapter_id: string;
  status: StorySessionStatus;
  state: StorySessionState;
  current_chapter: StoryChapter | null;
  ending: StoryEnding | null;
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
  hint: string | null;
  new_clues: string[];
  new_rewards: StoryReward[];
  session: StorySessionResponse;
}

export interface FutureLetterResponse {
  status: "ready";
  story_session_id: string;
  postcard_id: string;
  image_url: string;
  scene_source: "ai";
  generated_at: string;
  reflection_truncated: boolean;
}
