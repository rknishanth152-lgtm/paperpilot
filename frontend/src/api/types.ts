// Response contracts of the backend document API (backend/app/schemas/documents.py).
// Keep these in step with the Pydantic models; the frontend shows these values
// and never re-derives statuses, pages or evidence.

export type DocumentStatus = "pending" | "processing" | "parsed" | "failed";

export interface DocumentResponse {
  document_id: string;
  status: DocumentStatus;
  failure_reason: string | null;
  failure_explanation: string | null;
  original_filename: string | null;
  sha256: string;
  size_bytes: number;
  created_at: string;
  updated_at: string;
}

export interface UploadResponse extends DocumentResponse {
  created: boolean;
}

export type PassageRegion = "abstract" | "body" | "caption" | "back";

export interface Passage {
  passage_id: string;
  ordinal: number;
  region: PassageRegion;
  back_type: string | null;
  section_number: string | null;
  section_title: string | null;
  text: string;
  page_start: number | null;
  page_end: number | null;
}

export interface StructureResponse {
  document_id: string;
  status: "parsed";
  parser: { name: string; version: string };
  page_count: number | null;
  paper: {
    paper_id: string;
    title: string | null;
    authors: string[];
    abstract: string | null;
    doi: string | null;
  };
  passages: Passage[];
}
