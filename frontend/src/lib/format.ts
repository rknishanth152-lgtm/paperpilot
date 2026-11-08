// Pure display helpers. They format stored values; they never infer missing ones.

import type { Passage } from "../api/types";

/** "page 3", "pages 2–4", or "page unknown" when the page is not stored (DR-007). */
export function formatPages(start: number | null, end: number | null): string {
  if (start === null) return "page unknown";
  if (end === null || end === start) return `page ${start}`;
  return `pages ${start}–${end}`;
}

/** The heading a passage belongs under, from its stored section and region. */
export function sectionLabel(passage: Passage): string {
  const title = [passage.section_number, passage.section_title]
    .filter((part): part is string => part !== null && part !== "")
    .join(" ");
  if (title) return title;
  switch (passage.region) {
    case "abstract":
      return "Abstract";
    case "caption":
      return "Figure and table captions";
    case "back":
      return passage.back_type ? `Back matter: ${passage.back_type}` : "Back matter";
    case "body":
      return "Untitled section";
  }
}

export interface PassageGroup {
  key: string;
  label: string;
  passages: Passage[];
}

/** Consecutive passages under the same heading, in stored order. */
export function groupPassages(passages: Passage[]): PassageGroup[] {
  const groups: PassageGroup[] = [];
  for (const passage of passages) {
    const label = sectionLabel(passage);
    const last = groups.at(-1);
    if (last && last.label === label) {
      last.passages.push(passage);
    } else {
      groups.push({ key: passage.passage_id, label, passages: [passage] });
    }
  }
  return groups;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} bytes`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
