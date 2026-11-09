// Words people see for internal values. Internal names stay in the code and the
// API; nothing on screen should need knowledge of how PaperPilot is built.

import type { CitationFailure, DocumentStatus } from "../api/types";

export const STATUS_TEXT: Record<DocumentStatus, string> = {
  pending: "Waiting to start",
  processing: "Reading this paper…",
  parsed: "Ready to read",
  failed: "Couldn't read this file",
};

export const CITATION_FAILURE_TEXT: Record<CitationFailure, string> = {
  passage_not_found: "Source not found",
  not_in_context: "Not among the parts read",
  wrong_paper: "From a different paper",
  quote_mismatch: "Quote not found in the paper",
};

export function searchMethodText(method: string | null): string {
  if (method === "semantic_cosine") return "by meaning";
  if (method === "keyword_full_text") return "by matching words";
  return "with no search";
}

export function partsText(count: number): string {
  return `${count} ${count === 1 ? "part" : "parts"}`;
}
