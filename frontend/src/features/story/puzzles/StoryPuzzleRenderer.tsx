import type { StoryPuzzleData } from "../types";
import { MappingPuzzle } from "./MappingPuzzle";
import { MultiSelectPuzzle } from "./MultiSelectPuzzle";
import { SingleChoicePuzzle } from "./SingleChoicePuzzle";

interface StoryPuzzleRendererProps {
  puzzle: StoryPuzzleData;
  disabled?: boolean;
  onSubmit: (answer: unknown) => void;
}

export function StoryPuzzleRenderer({
  puzzle,
  disabled = false,
  onSubmit,
}: StoryPuzzleRendererProps) {
  switch (puzzle.type) {
    case "multi_select":
      return (
        <MultiSelectPuzzle
          puzzle={puzzle}
          disabled={disabled}
          onSubmit={onSubmit}
        />
      );
    case "mapping":
      return (
        <MappingPuzzle
          puzzle={puzzle}
          disabled={disabled}
          onSubmit={onSubmit}
        />
      );
    case "single_choice":
      return (
        <SingleChoicePuzzle
          puzzle={puzzle}
          disabled={disabled}
          onSubmit={onSubmit}
        />
      );
    default:
      return null;
  }
}
