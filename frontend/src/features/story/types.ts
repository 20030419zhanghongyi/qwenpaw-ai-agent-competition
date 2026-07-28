export interface StoryAssetRef {
  asset_id: string;
  alt?: string;
  caption?: string;
  role?: string;
}

export interface StoryDialogueLine {
  id?: string;
  speaker_id?: string;
  speaker: string;
  text: string;
  portrait_asset_id?: string;
  tone?: string;
}

export interface StoryKnowledgeCardData {
  id?: string;
  kind?: string;
  title: string;
  text?: string;
  content?: string;
  source_label?: string;
  confidence?: number | string;
}

export interface StoryPuzzleOption {
  id: string;
  text: string;
  description?: string;
  source_label?: string;
  asset_id?: string;
}

export interface StoryPuzzleField {
  id: string;
  label: string;
  description?: string;
}

interface StoryPuzzleBase {
  id: string;
  prompt: string;
  hints?: string[];
  explanation?: string;
  skip_text?: string;
}

export interface MultiSelectPuzzleData extends StoryPuzzleBase {
  type: "multi_select";
  options: StoryPuzzleOption[];
  min_selections?: number;
  max_selections?: number;
}

export interface MappingPuzzleData extends StoryPuzzleBase {
  type: "mapping";
  fields: StoryPuzzleField[];
  options: StoryPuzzleOption[];
}

export interface EvidenceChainPuzzleData extends StoryPuzzleBase {
  type: "evidence_chain";
  options: StoryPuzzleOption[];
  required_count?: number;
}

export interface AssemblyPuzzleData extends StoryPuzzleBase {
  type: "assembly";
  options: StoryPuzzleOption[];
  slots?: StoryPuzzleField[];
  slot_count?: number;
}

export interface LegacySingleChoicePuzzleData extends StoryPuzzleBase {
  type: "single_choice";
  options: StoryPuzzleOption[];
}

export type StoryPuzzleData =
  | MultiSelectPuzzleData
  | MappingPuzzleData
  | EvidenceChainPuzzleData
  | AssemblyPuzzleData
  | LegacySingleChoicePuzzleData;

export interface StoryAgentContextData {
  persona?: string;
  poi_name?: string;
  chapter_title?: string;
  chapter_goal?: string;
  known_facts?: string[];
  fiction_boundaries?: string[];
  suggested_questions?: string[];
  do_not_reveal?: string[];
}

export interface StoryAgentAnswer {
  text: string;
  source?: string;
  webUsed?: boolean;
  webSources?: Array<{ title?: string; url?: string; source?: string }>;
}
