import {
  READONLY_BLOCK_INFO,
  SOURCE_DISPLAY,
  type SelectedBlock,
  type SourceType,
} from "./parsePrompt";

export type ReadOnlyBlock = Exclude<SelectedBlock, { kind: "source" }>;

export type ReadOnlyBlockMeta =
  | {
      label: string;
      color: string;
      dragId: string;
      description: string;
      markerText: string;
      iconKind: "glyph";
      glyph: string;
    }
  | {
      label: string;
      color: string;
      dragId: string;
      description: string;
      markerText: string;
      iconKind: "source";
      sourceType: SourceType;
    };

export function getReadOnlyBlockMeta(block: ReadOnlyBlock): ReadOnlyBlockMeta {
  if (block.kind === "experiences") {
    const info = READONLY_BLOCK_INFO.experiences;
    return {
      label: info.label,
      color: info.color,
      dragId: "chip-experiences",
      description: info.description,
      markerText: "[[experiences]]",
      iconKind: "glyph",
      glyph: info.glyph,
    };
  }

  if (block.kind === "active_tasks") {
    const info = READONLY_BLOCK_INFO.active_tasks;
    return {
      label: info.label,
      color: info.color,
      dragId: "chip-active_tasks",
      description: info.description,
      markerText: "[[active_tasks]]",
      iconKind: "glyph",
      glyph: info.glyph,
    };
  }

  // source_data
  const sourceDisplay = SOURCE_DISPLAY[block.sourceType];
  return {
    label: `${sourceDisplay.label} Data`,
    color: READONLY_BLOCK_INFO.source_data.color,
    dragId: `chip-source_data-${block.sourceType}`,
    description: READONLY_BLOCK_INFO.source_data.description,
    markerText: `[[source_data:${block.sourceType}]]`,
    iconKind: "source",
    sourceType: block.sourceType,
  };
}

export function isReadOnlyBlockSelected(
  block: ReadOnlyBlock,
  selectedBlock: SelectedBlock | null,
): boolean {
  if (block.kind === "experiences") return selectedBlock?.kind === "experiences";
  if (block.kind === "active_tasks") return selectedBlock?.kind === "active_tasks";
  return selectedBlock?.kind === "source_data" && selectedBlock.sourceType === block.sourceType;
}
