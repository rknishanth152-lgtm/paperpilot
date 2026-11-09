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

export interface LibraryDocument {
  document_id: string;
  status: DocumentStatus;
  failure_explanation: string | null;
  original_filename: string | null;
  title: string | null;
  created_at: string;
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

// Answering: backend/app/schemas/answer_response.py.

export type CitationFailure =
  | "passage_not_found"
  | "not_in_context"
  | "wrong_paper"
  | "quote_mismatch";

export interface CitationResponse {
  alias: string;
  quote: string | null;
  valid: boolean;
  reason: CitationFailure | null;
  passage_id: string | null;
}

export interface StatementResponse {
  text: string;
  citations: CitationResponse[];
  has_valid_citation: boolean;
}

export interface EvidencePassage {
  alias: string;
  passage_id: string;
  document_id: string;
  paper_id: string;
  paper_title: string | null;
  section: string | null;
  page_start: number | null;
  page_end: number | null;
  text: string;
}

export type ReportingStatus =
  | "reported"
  | "partially_reported"
  | "not_found"
  | "needs_review";

export interface AssessmentEvidence {
  passage_id: string;
  section: string | null;
  page_start: number | null;
  page_end: number | null;
  quote: string;
  text: string;
}

export interface AssessmentItem {
  key: string;
  title: string;
  question: string;
  status: ReportingStatus;
  status_label: string;
  status_description: string;
  review_reason: "parse_incomplete" | "evidence_unverified" | "model_uncertain" | null;
  explanation: string | null;
  passages_examined: number;
  evidence: AssessmentEvidence[];
}

export interface AssessmentResponse {
  assessment_id: string;
  document_id: string;
  checklist_version: string;
  document_status: DocumentStatus;
  model: string | null;
  prompt_version: string | null;
  retrieval_method: string | null;
  created_at: string;
  items: AssessmentItem[];
}

export interface AnswerResponse {
  statements: StatementResponse[];
  evidence: EvidencePassage[];
  evidence_sufficiency: "sufficient" | "partial" | "insufficient";
  limitations: string | null;
  validation_status: "validated" | "failed";
  claim_support: "not_evaluated";
  retrieved_passage_ids: string[];
  passages_dropped: number;
  retrieval_method: string;
  model: string | null;
  prompt_version: string | null;
}
