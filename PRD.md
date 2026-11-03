# PaperPilot: Product Requirements Document

| Field | Value |
|---|---|
| Version | 0.5 (Phase 1 answers to OQ-001, -002, -003, -005, -013, -016 recorded, 2026-11-03; see `progress.md` §6.9) |
| Date | 2026-11-03 |
| Status | Planning. No application code exists yet (see `progress.md`). |
| Companion documents | `CLAUDE.md` (development rules), `progress.md` (actual state), `docs/implementation-roadmap.md` (sequence and exit criteria) |

## How this document is organised and how to read its labels

Requirements are stable-ID'd so that the roadmap, progress file and tests can refer to them. A change to an ID's meaning requires a note in `progress.md`.

| Label | Meaning |
|---|---|
| **[P]** | Project requirement. Comes from the PaperPilot project definition. |
| **[E]** | Engineering recommendation. My judgment; open to revision. |
| **[T]** | Supported by the earlier transcript analysis (notes in `notes/`), which in turn describes two videos. Used only where the transcript actually showed it. |
| **[A]** | Unverified assumption. Must be checked before relying on it. |
| **[Q]** | Open question. Registered in section 13 (`OQ-xxx`). |

Unlabelled requirement text is **[P]** unless the Basis column says otherwise.

**Conflict rule:** the explicit project definition outranks the transcript notes. Conflicts and their resolution are listed in Appendix A.

---

## 1. Product overview

### 1.1 Name and description

**PaperPilot** is an evidence-first research intelligence and scientific reproducibility platform. It turns academic papers into structured, searchable, interconnected and verifiable knowledge.

### 1.2 Problem

Papers spread objectives, methods, datasets, settings, metrics, results and limitations across sections, tables, figures and supplements. Finding them by hand is slow. A general-purpose LLM summary is fast but can omit context, misstate results, or attach citations that do not support the claim.

### 1.3 Proposed solution

Combine: scholarly document parsing, structured extraction, evidence-linked retrieval, citation validation, cross-paper comparison, and reproducibility assessment. Every derived statement stays connected to a stored source passage.

### 1.4 Vision

A student or researcher can move from "which papers?" to "what exactly did they report, where, and what is missing?" while always being able to inspect the source text behind every statement.

### 1.5 Core principles

> **Evidence before inference. Traceability before convenience. Measurable correctness before impressive demonstrations.** [P]

1. **Preserve provenance.** Derived data links to source passages (`DR-001`).
2. **Separate source from interpretation.** Source text and machine-generated claims live in different tables (`DR-002`).
3. **Validate structured output.** Model output is untrusted input (`FR-QA-003`, `FR-EXT-002`).
4. **Prefer deterministic checks.** Use ordinary code for anything that can be checked by code (`FR-CIT-001`).
5. **Measure retrieval separately from answers.** (`FR-EVL-002`).
6. **Preserve uncertainty.** Missing, ambiguous, failed and verified-absent are different states (`DR-006`).
7. **Preserve experimental context.** Never compare results because they share a table (`FR-CMP-003`).
8. **Build incrementally.** Each feature has defined inputs, outputs, validation and tests.

### 1.6 Terminology (binding)

All documents use these terms. Where two terms look similar, the distinction matters.

| Term | Definition |
|---|---|
| **Paper** | A scholarly work as a logical entity (identified by DOI when available). Metadata-level. |
| **Document** | One specific uploaded file (a PDF) belonging to a paper, identified by its content hash. A paper can have several documents (e.g. preprint and publisher version). |
| **Section** | A structural unit with a heading, as reported by the parser. |
| **Passage** | The smallest independently retrievable and citable unit of source text (initially a paragraph). Belongs to one document; carries section and page information when known. Immutable once stored. |
| **Source evidence** | Original text stored as a passage, plus a quotation taken from it. |
| **Extracted item** | A machine-generated interpretation (for example "dataset: X") that links to source evidence. A candidate until verified. |
| **Citation** | A reference from an answer statement to a passage. |
| **Citation validity** | The cited passage exists, belongs to the correct document/paper in scope, and any supplied quotation is present in it. Deterministic. |
| **Claim support** | The cited evidence actually supports the statement. Semantic. Not automated in the MVP. |
| **Not found** | The information was not found in the material examined. Not proof of absence. |
| **Absent (verified)** | A human confirmed the paper does not report it. Future capability. |
| **Retrieval relevance** | Whether the retrieved passages contain the needed evidence. |
| **Answer correctness** | Whether the final answer is right. A good answer can follow poor retrieval by luck, and the reverse. |
| **Reported result** | A number a paper states, with its dataset, metric, split and conditions. |
| **Comparable result** | Two reported results whose context fields match well enough for comparison (`FR-CMP-003`). |
| **Planned vs completed** | Planned work is described in the roadmap. Completed work appears only in `progress.md` with evidence. |

---

## 2. Users and use cases

No market research, adoption data or business claims are asserted. These are needs inferred from the project definition.

| User | Need | Primary workflow |
|---|---|---|
| **Student researching a topic** | Learn what a set of papers did, with enough evidence to cite correctly and without reading every page. | Upload paper(s) → inspect structure → ask questions → read evidence passages. (Later: discover papers, extract datasets/metrics.) |
| **Researcher reviewing related papers** | Compare methods, datasets, metrics and results without mixing up experimental conditions. | Upload several papers → review extracted items → build a comparison matrix → check comparability labels. |
| **User checking what a paper reports** | Know whether a paper provides the details needed to understand or attempt to repeat its experiments. | Upload one paper → review a reporting checklist with evidence per item. |

Secondary: developers studying existing methods, research teams comparing published results.

---

## 3. Goals and non-goals

### 3.1 MVP goals

1. **VS-1 (vertical slice):** upload a permitted PDF, parse with GROBID, store document and passages, retrieve by keyword, answer from retrieved evidence, validate the citation references. (Section 12.)
2. **MVP-1:** extend VS-1 with a repeatable evaluation harness, structured extraction of datasets/metrics/limitations, semantic and hybrid retrieval *if evaluation shows a benefit*, OpenAlex discovery, a comparison matrix built from extracted items, and an evidence-backed reproducibility checklist.
3. Every shipped capability has observable acceptance criteria and tests.

### 3.2 Non-goals for the MVP

| Excluded | Reason / what would reopen it |
|---|---|
| Authentication, authorization, multi-user collaboration | The MVP is a single-user local application and **must not be exposed on a shared network** (`NFR-SEC-006`). Reopen when more than one person needs separate data. |
| Microservices, Kubernetes, queues/workers (Redis, Celery) | A modular monolith suffices. Reopen when measured ingestion load or timeouts justify (`AD-010`). |
| Autonomous or multi-agent orchestration, agent tool loops | A simple, inspectable RAG pipeline is a project requirement. Reopen only if evaluation shows single-pass RAG fails. |
| Arbitrary code execution, running code from papers or repositories | Safety. Code-repository analysis is a future capability (static only). |
| Claims of discovering definitive research gaps | AI suggestions are hypotheses, never proven gaps. |
| An automated "reproducibility verdict" or score | Out of scope; the checklist reports reporting status only (`FR-REP-004`). |
| Knowledge graph | Future. Do not build in the vertical slice. |
| OCR of scanned PDFs | Scanned/image-only PDFs are detected and rejected with a clear status (`FR-ING-003`). Reopen if users need them. |
| Production-scale deployment, cloud infrastructure, real-time infrastructure | Premature. |
| Multiple discovery providers | OpenAlex only. |
| Complex ranking/reranking | Only as a measured experiment after the baseline. |

**Extension points are not features.** A boundary such as the storage interface (`AD-002`) exists to avoid rewrites, not to deliver S3 support.

---

## 4. Architecture overview and decisions

### 4.1 Shape

A **modular monolith**: one React/TypeScript frontend, one FastAPI backend, one PostgreSQL database, and the GROBID service as the only separate runtime dependency.

```
Browser (React/TS/Vite)
   │ HTTP/JSON
   ▼
FastAPI backend ── modules: api · schemas · models/database · services/
   │                         discovery · ingestion · extraction · retrieval ·
   │                         comparison · reproducibility
   ├──► PostgreSQL (source of truth: papers, documents, passages, later items/evidence)
   ├──► Local filesystem via a storage interface (original PDFs, raw parser output)
   ├──► GROBID (HTTP, internal only)
   ├──► LLM provider (via a thin provider-independent interface)
   └──► OpenAlex (Phase 9)
```

### 4.2 Core data flow (VS-1)

1. Client uploads a PDF → backend validates and stores it → creates a `document` (`pending`).
2. Backend sends the PDF to GROBID → receives TEI/XML → stores the raw output → derives metadata, sections and passages → document becomes `parsed` or `failed`.
3. Client asks a question scoped to selected paper(s) → backend runs keyword retrieval over passages → builds a bounded context with prompt-local passage aliases.
4. One LLM call returns a structured answer (statements, citations, sufficiency).
5. Backend validates the output schema, resolves aliases to real passage IDs, and runs deterministic citation checks.
6. Response contains the answer, per-citation validity, evidence passages with section/page from the database, and `claim_support: not_evaluated`.

### 4.3 Architecture decisions

Basis column: **[P]** project direction, **[E]** engineering recommendation, **[T]** transcript-supported pattern.

| ID | Decision | Reason | Alternatives / trade-offs | Revisit if | Basis |
|---|---|---|---|---|---|
| AD-001 | Modular monolith with package boundaries per capability. | One deployable unit keeps the MVP comprehensible. | Microservices: operational cost with no demonstrated need. | A module needs independent scaling or deployment. | [P] |
| AD-002 | PostgreSQL is the source of truth. Files on local disk behind a small storage interface (save/read/delete by key). | Spec separates relational data from file storage. The interface avoids a later rewrite. | Storing PDFs in Postgres: harder to inspect, no benefit. Supabase Storage (used in both videos): adds a hosted dependency not in the spec. | Object storage is justified by deployment. | [P] |
| AD-003 | GROBID is the initial parser. Feasibility is **unproven** until Phase 1 (`OQ-001`, `OQ-002`, `OQ-015`, `OQ-016`). | Project direction; designed for scholarly structure. | Docling (used in both videos, but on SEC filings and appliance manuals, not papers) as a documented fallback only if Phase 1 shows GROBID inadequate. | Phase 1 findings. | [P] |
| AD-004 | Passage = one paragraph from the parsed body, with section and page when known. | Smallest unit that is readable as evidence. A hypothesis. Phase 1 (2026-11-03): paragraph stands, with two provisional repair rules: re-join a paragraph split mid-sentence at a column or page break, and skip paragraphs with no letters while recording the count (`docs/experiments/grobid-feasibility.md` §7, `OQ-002`). | Fixed-size token chunks (shown in the videos) lose section boundaries; sentence-level may fragment meaning. | Phase 1 inspection or Phase 4 Recall@5 shows poor boundaries. | [E] |
| AD-005 | Keyword retrieval (PostgreSQL full-text search) first; establish a measured baseline before semantic search. | Project requirement. Simple and inspectable. | Semantic first: needs an embedding model, cost and an index before a baseline exists. | Never skip the baseline. | [P] |
| AD-006 | Plain RAG: one retrieval step, one LLM call, structured output. No agent loop. | Project requirement. The agent-loop build in the videos took about a minute and an estimated $1–2 per query with a frontier model, and its behaviour was not validated by its author. | Agent loop: can self-correct; hard to evaluate and cost-control. | Evaluation shows single-pass answers fail on questions needing multiple lookups. | [P][T] |
| AD-007 | The LLM cites **prompt-local aliases** (e.g. `P1`, `P2`), mapped by code to real passage IDs. Page and section shown to users always come from the database, never from model output. | Short, checkable identifiers. Prevents fabricated pages. | Letting the model emit UUIDs or page numbers: easier to fabricate and harder to read. | Alias scheme proves error-prone. | [E] |
| AD-008 | Citation validity is deterministic code. Claim support is a separate, non-automated measure in the MVP (human-labelled sample). | Structural validity does not prove semantic support. | LLM-judge claim support: unvalidated; consider only as a measured experiment. | A validated judge exists. | [P] |
| AD-009 | No authentication in the MVP. Single-user, local. | Project non-goal. | Supabase-style auth/RLS as in the videos: unneeded here. | Any shared or networked deployment. | [P] |
| AD-010 | Ingestion runs in the API process with status polling (no queue). Documents stuck `processing` after a restart are recovered (`FR-ING-010`). | Avoids Redis/Celery before need. | A worker queue. | Measured parse times or concurrency make request-bound work unacceptable. | [P][E] |
| AD-011 | A thin LLM/embedding interface plus a fake implementation for tests. | Concrete benefit: deterministic tests and provider switching. Not a framework. | Provider SDK calls throughout; or a heavy orchestration framework. | None expected. | [P][E] |
| AD-012 | SQLAlchemy 2.x models and Alembic migrations. | Alembic is required; it is built on SQLAlchemy. A SQLAlchemy+Alembic flow was demonstrated in one video, including a driver-URL gotcha [T]. Confirm the exact version and driver (`OQ-014`). | SQLModel; raw SQL migrations. | Setup decision. | [P][T][A] |
| AD-013 | Extracted items, evidence links and (later) reproducibility items are separate tables from passages. | Source-vs-interpretation separation (`DR-002`). | A JSON blob on documents. | None. | [P] |
| AD-014 | Embeddings (Phase 8) live in their own table keyed by passage and embedding model. | Lets the model change without touching passages. | A vector column on `passages`. | Phase 8 design review (`OQ-012`). | [E][Q] |
| AD-015 | Docker Compose runs PostgreSQL and GROBID for development; backend and frontend run on the host. Choose a Postgres image that can later enable pgvector, but do not enable it until Phase 8. | GROBID is a separate Java service. Compose makes the environment repeatable. Image names/tags must be verified, not guessed (`OQ-015`). | Installing both natively. | Compose proves harder than native on the developer's machine. | [E][A] |
| AD-016 | Observability in the MVP is structured logging only. | Enough for a single-user tool. The CC video used a hosted tracing product; it is not required. | Tracing platform. | Debugging LLM pipelines becomes the bottleneck (`OQ-016`). | [E][T] |

---

## 5. Functional requirements

**Reading the tables:** "Phase" refers to `docs/implementation-roadmap.md`. "Scope" is **VS-1** or **MVP-1**. Failure cases listed are the ones the acceptance criteria must exercise. Unless stated, all errors return a structured error response without internal stack traces (`NFR-SEC-005`).

### 5.1 Ingestion and parsing (`FR-ING`)

| ID | Requirement (what / why) | Input → Output | Failure cases | Acceptance criteria | Scope · Phase · Depends |
|---|---|---|---|---|---|
| FR-ING-001 | Accept one PDF upload and validate it before storing, to avoid processing non-PDFs or oversized files. | multipart file → `document_id` and `pending` status | Not a PDF; wrong magic bytes; empty file; over size limit; filename with path characters | A text file renamed `.pdf` is rejected. A file over the limit is rejected. Valid PDF returns a `document_id`. The client filename is never used as a path. | VS-1 · P3 · FR-ING-002 |
| FR-ING-002 | Store the original file unmodified through the storage interface under a generated key, and record its SHA-256, to allow duplicate detection and re-processing. | validated bytes → `storage_key`, `sha256`, `size_bytes` | Disk write failure; storage key collision | Stored bytes hash equals recorded hash. A write failure leaves no `document` row claiming success. | VS-1 · P3 |
| FR-ING-003 | Track processing status with explicit values `pending`, `processing`, `parsed`, `failed` and a `failure_reason` code, so failures are never shown as success. | document → status | Parser unreachable; parser timeout; HTTP 204 (no content) or 503 from GROBID; empty or unusable parse (no body passages); likely scanned PDF; malformed TEI | Each failure above produces `failed` with a distinct reason code, no passages, and a retrievable error message. A `parsed` document has at least one passage. | VS-1 · P3 · FR-ING-004 |
| FR-ING-004 | Send the PDF to GROBID's full-text processing endpoint and record parser name and version/configuration with the document. Endpoint and options to be verified against current GROBID docs (`OQ-015`). | stored PDF → TEI/XML | Connection refused; timeout; non-200 status; invalid XML | Integration test against a running GROBID returns parseable TEI for a sample paper. Simulated GROBID failures map to documented reason codes. | VS-1 · P3 · P1 findings |
| FR-ING-005 | Persist the raw parser output as an artifact through the storage interface, so passages can be re-derived and parser behaviour inspected. | TEI → artifact key on document | Storage failure | Artifact exists and re-parsing it yields the same passages (deterministic derivation). | VS-1 · P3 |
| FR-ING-006 | Derive paper-level metadata (title, authors, abstract, DOI if present) from the parse, marked with source `grobid` and nullable. | TEI → `papers` fields | Missing title/authors/DOI; malformed values | Missing metadata is stored as null, not as empty or invented strings. A paper without DOI is still created. | VS-1 · P3 |
| FR-ING-007 | Create passages from the parsed body: ordinal, section title/path, page start/end (null when unknown), text. Exclude the bibliography from retrievable passages by default (`OQ-003`). | TEI → `passages` rows | No headings; no page data; repeated headers/footers leaking into text; very long or very short paragraphs | Passages keep source order. Unknown page is stored as null, never 0. Text equals the TEI text after documented normalization. | VS-1 · P3 · FR-ING-004 |
| FR-ING-008 | Handle repeat, duplicate and updated uploads (see 8.3): identical hash returns the existing document; same DOI creates a new document under the same paper; failed documents can be retried. | upload → existing or new `document_id` | Same file twice; same DOI different file; concurrent identical uploads | Uploading the same file twice yields one document and one set of passages. Two different PDFs with one DOI yield one paper and two documents. Retrying a failed document does not create duplicate passages. | VS-1 · P2/P3 · FR-ING-002 |
| FR-ING-009 | Expose a read endpoint returning a document's metadata, sections and passages, so a user can inspect what the parser produced. | `document_id` → structure | Unknown id; document not `parsed` | Returns passages in order with section and page (or "unknown"). A non-parsed document returns its status and reason. | VS-1 · P3 |
| FR-ING-010 | Recover from interrupted processing: on startup (or after a timeout) documents left `processing` are marked `failed` with reason `interrupted` and may be retried. | startup scan | Process killed mid-parse | Test simulating a stale `processing` row confirms it becomes `failed/interrupted`. | VS-1 · P3 · AD-010 |

### 5.2 Retrieval (`FR-RET`)

| ID | Requirement | Input → Output | Failure cases | Acceptance criteria | Scope · Phase · Depends |
|---|---|---|---|---|---|
| FR-RET-001 | Maintain a full-text search representation for every passage, so keyword retrieval works without an external index. Language configuration is an open decision (`OQ-004`). | passage text → search vector | Text with unusual symbols; null text | Every stored passage has an index entry. Adding a passage requires no manual reindex. | VS-1 · P4 · FR-ING-007 |
| FR-RET-002 | Provide keyword retrieval: ranked passages for a question, scoped to selected papers/documents, with a result limit `k`. | question, scope, k → list of {passage_id, document_id, paper_id, section, page, text, score} | No match; empty query; punctuation-only query; very long query; unknown scope id | No match returns an empty list (not an error). Results come only from `parsed` documents in scope. Ordering is deterministic for equal scores. | VS-1 · P4 |
| FR-RET-003 | Treat the user's question as data: use parameterised queries and a query-parsing function that does not raise syntax errors on arbitrary text (candidate functions in `OQ-004`). | raw text → safe query | Quotes, operators, SQL fragments | A test with SQL-like and operator-like input returns results or an empty list and never errors or alters data. | VS-1 · P4 |
| FR-RET-004 | Make retrieval callable without an LLM so it can be evaluated on its own. | function call | — | The evaluation harness runs retrieval alone. | VS-1 · P4 |
| FR-RET-005 | Semantic retrieval: embed passages and queries and search by vector similarity using pgvector. Provider-independent embedding interface. | passages → embeddings; query → similar passages | Embedding API failure; dimension mismatch; passage not embedded | Embedding dimension is validated against the stored model. Missing embeddings are reported, not silently skipped. | MVP-1 · P8 |
| FR-RET-006 | Hybrid retrieval: combine keyword and semantic results through a documented merge method (Reciprocal Rank Fusion is one candidate). | two ranked lists → one list | One method fails or returns nothing | If one method is unavailable, the other still answers and the response indicates which methods contributed. | MVP-1 · P8 |
| FR-RET-007 | Compare keyword, semantic and hybrid retrieval on the same evaluation set and record the result. | eval set → metrics | — | A recorded comparison exists. A method becomes the default only if the recorded results justify it. | MVP-1 · P8 · FR-EVL-002 |

### 5.3 Question answering (`FR-QA`)

| ID | Requirement | Input → Output | Failure cases | Acceptance criteria | Scope · Phase · Depends |
|---|---|---|---|---|---|
| FR-QA-001 | Answer a natural-language question about selected paper(s) using only retrieved passages. | question, scope → answer object (9.1) | No scope; unknown paper | Response contains the fields in 9.1 and nothing else is presented as evidence. | VS-1 · P5 |
| FR-QA-002 | Prepare a bounded context: top-k passages with prompt-local aliases, section and paper labels, and an explicit truncation rule. Passage text is delimited as data. | passages → prompt context | Context exceeds budget | Truncation is deterministic and reported (e.g. `passages_dropped`). Aliases map back to unique passage IDs. | VS-1 · P5 · FR-RET-002 |
| FR-QA-003 | Require structured model output and validate it against a schema. Malformed output yields an explicit error after a documented retry policy, never a free-text fallback. | model output → validated object | Invalid JSON; missing fields; extra fields; wrong types | Fault-injection tests with malformed outputs return a structured error and no answer is displayed as evidence-backed. | VS-1 · P5 |
| FR-QA-004 | Handle insufficient evidence: if retrieval returns nothing, skip the LLM and return `insufficient`. If the model declares insufficiency, preserve it; do not attach a confident answer. | — | — | A question with no matching passages returns `insufficient` without an LLM call. An out-of-corpus question in the evaluation set does not produce a cited factual answer. | VS-1 · P5 |
| FR-QA-005 | Isolate model access behind one interface with a fake implementation for tests. | prompt → structured output | Provider timeout; rate limit; auth failure | All QA tests run offline with the fake. Provider errors return an explicit error, never an invented answer. | VS-1 · P5 · AD-011 |
| FR-QA-006 | Each response reports the model identifier, the retrieved passage IDs, and which retrieval method produced them, so answers are auditable. | — | — | Response includes `model`, `retrieved_passage_ids`, `retrieval_method`. | VS-1 · P5 |
| FR-QA-007 | Treat passage text as untrusted. Instructions inside passages must not be followed. | — | Passage containing "ignore previous instructions" | A test passage containing an instruction does not change the response structure or citation behaviour. (Limits of this defence are in `RISK-08`.) | VS-1 · P5 |

### 5.4 Citation validation (`FR-CIT`)

| ID | Requirement | Input → Output | Failure cases | Acceptance criteria | Scope · Phase · Depends |
|---|---|---|---|---|---|
| FR-CIT-001 | Validate every citation deterministically: the alias resolves; the passage exists; it belongs to a document of a paper in scope; it was in the context given to the model. | answer + context map → per-citation result | Nonexistent ID; passage from another paper; passage not in context | Given a stored passage ID in scope, the validator accepts it. Given a nonexistent ID or a passage from a paper outside the scope, it rejects it, with reason codes `passage_not_found`, `wrong_paper`, `not_in_context`. | VS-1 · P5 · FR-QA-002 |
| FR-CIT-002 | When a citation includes a quotation, verify it is contained in the cited passage after documented normalisation (whitespace, hyphenation, ligatures: `OQ-013`). | quote, passage → match / mismatch | Altered quote; quote from a different passage | Exact quote accepted. Altered quote rejected with `quote_mismatch`. | VS-1 · P5 |
| FR-CIT-003 | Page and section displayed with a citation come from the passage record. Model-supplied page numbers are ignored or checked, never trusted. | — | Model supplies a wrong page | A test with a wrong model-supplied page shows the stored page (or "unknown"). | VS-1 · P5 |
| FR-CIT-004 | Report validation per citation and per answer: `validation_status` is `validated` only if all citations are valid and **every statement** in a `sufficient` or `partial` answer has at least one valid citation. An `insufficient` answer contains no statements (only `limitations`). | — | Any statement without a citation; any invalid citation; an `insufficient` answer that contains statements | An answer with an invalid citation, or with any uncited statement, is returned with `validation_status: failed` and must not be shown as evidence-backed. An `insufficient` answer with statements fails schema validation. | VS-1 · P5 |
| FR-CIT-005 | Report claim support honestly: `claim_support` is `not_evaluated` in every MVP response. Claim support is measured offline on a human-labelled sample (`FR-EVL-004`). | — | — | No response field implies semantic verification. | VS-1 · P5 |

### 5.5 Evaluation (`FR-EVL`)

| ID | Requirement | Input → Output | Failure cases | Acceptance criteria | Scope · Phase · Depends |
|---|---|---|---|---|---|
| FR-EVL-001 | Maintain a manually reviewed evaluation set of about 20 questions. Expected evidence is identified by paper plus a quote from the source text, not by database ID, because IDs change on re-ingestion. Include at least some questions the corpus cannot answer. | file in `benchmarks/` | Quote cannot be matched after re-parse | Each question lists the paper(s), expected supporting quote(s), and whether it is answerable. A review date and reviewer are recorded. | VS-1 · P4 |
| FR-EVL-002 | Compute Recall@5 for retrieval alone: a question counts as a hit if any expected supporting passage appears in the top 5. | eval set, retriever → metric | Expected quote not found in any stored passage (labelling error) | Output lists hits, misses, and unmatched expectations. Result is saved with date, code revision and configuration. | VS-1 · P4 · FR-RET-004 |
| FR-EVL-003 | Compute the citation reference-validity rate over evaluation answers. | answers → rate | — | Reported as validated / total, with failure reasons. | VS-1 · P6 |
| FR-EVL-004 | Compute the claim-support rate from human labels on a sample of statements, using a fixed labelling guide. | labelled statements → rate | Labeller disagreement | The guide, sample size and labeller are recorded. The rate is reported with its sample size. | VS-1 · P6 |
| FR-EVL-005 | Compute extraction precision, recall and F1 against labelled papers using a documented matching rule (`OQ-009`). | extractions, labels → P/R/F1 | Ambiguous matches | Matching rule is written down before scoring. | MVP-1 · P7 |
| FR-EVL-006 | Compute reproducibility classification accuracy against hand-labelled items. | — | — | Reported per status, including confusion between `not_found` and `needs_review`. | MVP-1 · P11 |
| FR-EVL-007 | If duplicate detection beyond identical-hash and DOI match is implemented, measure its precision and recall. | — | — | Applies only if fallback matching is built (`FR-DIS-002`). | MVP-1 · P9 |

All evaluation outputs are generated by the harness and saved as run artifacts. They are never edited by hand and never presented as targets achieved.

### 5.6 Structured extraction (`FR-EXT`)

| ID | Requirement | Input → Output | Failure cases | Acceptance criteria | Scope · Phase · Depends |
|---|---|---|---|---|---|
| FR-EXT-001 | Extract items of three types initially: `dataset`, `metric`, `limitation`, from a parsed document's passages. | document → extracted items | Document too long for one call (`OQ-009`); no items found | Each item has type, value text, model id, run id, status. "No items found" is recorded as an outcome, not as silence. | MVP-1 · P7 · FR-ING-007 |
| FR-EXT-002 | Validate model output against a schema; record failures. | model output → items or failure record | Malformed output | A malformed response creates a failed run record, not partial silent data. | MVP-1 · P7 |
| FR-EXT-003 | Every item must have at least one evidence link (passage + quotation). Verify quotation presence in the passage deterministically. Items with unmatched quotes are flagged `quote_unmatched` and excluded from comparisons by default. | item, passage → verification status | Fabricated quote | Fault-injection test with an invented quote yields `quote_unmatched`. | MVP-1 · P7 · FR-CIT-002 |
| FR-EXT-004 | Store extracted items separately from passages; never modify passage text. | — | — | Schema review confirms no extracted text is written into `passages`. | MVP-1 · P7 · DR-002 |
| FR-EXT-005 | Record each extraction run (model, prompt version, time). Re-running must not delete earlier runs or any item that a human has confirmed or corrected. | — | Re-run after correction | A re-run after a (simulated) confirmation leaves the confirmed item intact. | MVP-1 · P7 |
| FR-EXT-006 | Evaluate against hand-labelled papers (`FR-EVL-005`). | — | — | A recorded baseline exists before extraction is used by comparison. | MVP-1 · P7 |

### 5.7 Discovery (`FR-DIS`)

| ID | Requirement | Input → Output | Failure cases | Acceptance criteria | Scope · Phase · Depends |
|---|---|---|---|---|---|
| FR-DIS-001 | Search OpenAlex by keyword, title or DOI and return normalised metadata. Verify API details and limits in OpenAlex docs before implementation. | query → paper metadata list | API error; timeout; rate limit; malformed response | Errors are reported distinctly from "no results". | MVP-1 · P9 |
| FR-DIS-002 | Normalise DOIs and detect duplicates by DOI. Define fallback matching when DOI is absent (`OQ-007`). | — | Different DOI formats; same title different works | DOIs in different textual forms match. Fallback matches are flagged as probable, not certain. | MVP-1 · P9 |
| FR-DIS-003 | Keep three states distinct per paper: metadata only, open-access landing page reported, direct PDF link reported. Never imply a PDF is available or permitted. | — | Landing page mistaken for PDF | A record with only a landing page is shown as such. | MVP-1 · P9 |
| FR-DIS-004 | Reconstruct abstracts from the provider format where available; abstract is nullable. | — | Missing abstract | Null abstracts remain null. | MVP-1 · P9 |
| FR-DIS-005 | Adding a discovered paper never blocks manual upload; a discovered paper can later have a document attached. | — | — | Manual upload works with discovery disabled. | MVP-1 · P9 |

### 5.8 Comparison (`FR-CMP`)

| ID | Requirement | Input → Output | Failure cases | Acceptance criteria | Scope · Phase · Depends |
|---|---|---|---|---|---|
| FR-CMP-001 | Build a matrix for 2 or more papers over selected dimensions, using **only existing extracted items**. | paper ids, dimensions → matrix | Paper with no extractions | Missing cells show `not_extracted`, never a generated guess. | MVP-1 · P10 · FR-EXT-* |
| FR-CMP-002 | Every cell lists its items with evidence links. | — | — | Clicking/reading any cell yields the source quotation and location. | MVP-1 · P10 |
| FR-CMP-003 | Label each pair of reported results `directly_comparable`, `requires_context`, `not_comparable`, or `insufficient_information`, by deterministic rules over extracted dataset, metric, split/protocol and conditions. No ranking is produced unless `directly_comparable`. | results → label | Missing split; same dataset name different versions | Two results on different datasets are never `directly_comparable`. Missing context yields `insufficient_information`. Rules are documented and tested. | MVP-1 · P10 · `OQ-008` |
| FR-CMP-004 | Represent a reported result with dataset, metric, value, split, conditions and evidence. Representation is an open decision (`OQ-008`). | — | — | Decided and documented before Phase 10 starts. | MVP-1 · P10 |

### 5.9 Reproducibility (`FR-REP`)

| ID | Requirement | Input → Output | Failure cases | Acceptance criteria | Scope · Phase · Depends |
|---|---|---|---|---|---|
| FR-REP-001 | Maintain a small, versioned checklist definition (initial item set chosen in Phase 11: `OQ-010`). Candidate topics: dataset access, preprocessing, splits, architecture, hyperparameters, training procedure, metrics, baselines, seeds, code availability, environment. | — | — | The checklist version is stored with every assessment. | MVP-1 · P11 |
| FR-REP-002 | Assign each item exactly one status: `reported`, `partially_reported`, `not_found`, `needs_review`, with evidence and a record of the material examined (document, parse status). | document → item statuses | Document failed or partially parsed | A failed or incomplete parse never yields `not_found`; it yields `needs_review`. | MVP-1 · P11 |
| FR-REP-003 | `reported` and `partially_reported` require at least one verified evidence quotation. | — | Status without evidence | Fault-injection test: an item marked `reported` with no verified evidence is rejected. | MVP-1 · P11 · FR-CIT-002 |
| FR-REP-004 | No overall score, grade or "reproducible / irreproducible" verdict. User-facing text for `not_found` states it means "not found in the material examined". | — | — | UI/API review confirms the wording and absence of a verdict. | MVP-1 · P11 |
| FR-REP-005 | Evaluate against hand-labelled items (`FR-EVL-006`). | — | — | Baseline recorded before wider use. | MVP-1 · P11 |

### 5.10 Minimal user interface (`FR-UI`)

| ID | Requirement | Acceptance criteria | Scope · Phase |
|---|---|---|---|
| FR-UI-001 | Upload a PDF and see its processing status and failure reason. | Failed uploads display the reason code in plain language. | VS-1 · P3 |
| FR-UI-002 | Inspect parsed structure: metadata, sections, passages with page or "page unknown". | Passage text is shown exactly as stored. | VS-1 · P3 |
| FR-UI-003 | Ask a question, see the answer statements, each citation's validity, and the evidence passage with section/page; invalid or failed-validation answers are visibly marked and not presented as evidence-backed. | Failed validation cannot be mistaken for success. | VS-1 · P5 |

Later UI for extraction, comparison and checklists follows the same rule: every displayed value links to its evidence.

"Minimal" refers to **feature scope**, not quality. Every page meets `NFR-UX-001`.

---

## 6. Non-functional requirements

No latency guarantees or service-level targets are set. Items marked **baseline** are measured first and targets decided afterwards.

| ID | Dimension | Requirement |
|---|---|---|
| NFR-COR-001 | Correctness | No feature may present AI output as verified fact. Displayed evidence always comes from stored passages. |
| NFR-COR-002 | Correctness | Evaluation numbers appear only if produced by the harness (`FR-EVL`). |
| NFR-PRV-001 | Provenance | Every derived record links to passage(s) and records the producing model/parser version (see section 8). |
| NFR-REL-001 | Reliability | Parser, database, storage and model failures yield explicit statuses or errors. No misleading success states. |
| NFR-REL-002 | Reliability | Ingestion is idempotent for identical files (`FR-ING-008`). |
| NFR-REL-003 | Reliability | External calls (GROBID, LLM, OpenAlex) have configured timeouts. Default values are baseline to establish. |
| NFR-SEC-001 | Security | Never commit secrets. `.env` is ignored; `.env.example` has placeholders only. |
| NFR-SEC-002 | Security | Validate type by content (PDF signature), enforce size limits, generate storage keys, never use client filenames as paths. |
| NFR-SEC-003 | Security | Treat PDFs, parsed text and model outputs as untrusted. Do not execute code from papers. |
| NFR-SEC-004 | Security | GROBID is reachable only from the backend (not published beyond the local machine). |
| NFR-SEC-005 | Security | API errors do not expose stack traces, file paths, prompts or configuration. |
| NFR-SEC-006 | Security | The MVP has no authentication and must not be exposed to untrusted networks. |
| NFR-PRI-001 | Privacy | Paper text is sent to the configured LLM/embedding provider. Only upload papers whose terms permit that. Document this in `README.md`. |
| NFR-PRI-002 | Privacy | Logs must not contain full paper text or credentials. |
| NFR-MNT-001 | Maintainability | Module boundaries follow the capability list. Cross-module access goes through service functions, not table access. |
| NFR-MNT-002 | Maintainability | Schema changes only via migrations. |
| NFR-TST-001 | Testability | Unit tests (pure logic), integration tests (database, GROBID), API tests, evaluation tests. LLM-dependent tests use the fake provider. |
| NFR-TST-002 | Testability | Every fault-injection case named in this PRD has a test. |
| NFR-PRF-001 | Performance | Baseline to establish: parse time per paper, retrieval latency, answer latency, cost per answer. No targets until measured. |
| NFR-ACC-001 | Accessibility | UI is keyboard-operable, uses labelled form controls, and never relies on colour alone for status (validated/failed, reproducibility status). Detailed WCAG targets are not set for the MVP. |
| NFR-UX-001 | Interface quality | The UI has a coherent, distinctive visual identity suited to reading and checking evidence, not a generic dashboard template. Typography, spacing, colour, reusable components and information hierarchy follow shared tokens documented in `docs/design-system.md`. Motion is purposeful, restrained and consistent: it communicates state, hierarchy, causality or feedback, respects `prefers-reduced-motion`, and never shows invented progress. Every data view has distinct loading, empty, error and success states. Each implemented page and significant interaction is inspected in a running browser at representative narrow, medium and wide viewports before it is reported complete. Visual polish must not reduce reading comfort, accessibility (`NFR-ACC-001`), responsiveness or evidence traceability (`NFR-COR-001`). No numerical visual-quality targets are set, and no animation library is mandated (`OQ-014`). Adds no features: VS-1 scope is unchanged. |

---

## 7. User workflows

| # | Workflow | Steps | Scope |
|---|---|---|---|
| W1 | Upload and process a paper | Choose PDF → validation → stored → parse → status `parsed` or `failed` with reason | VS-1 |
| W2 | Inspect extracted document structure | Open document → see title/authors/abstract, sections, passages, page or "unknown" | VS-1 |
| W3 | Ask a question | Select paper(s) → ask → see statements with citations → open each cited passage → see validity status and `claim_support: not_evaluated` | VS-1 |
| W4 | Extract structured information | Run extraction → review items by type with quotes → note `quote_unmatched` items | MVP-1 |
| W5 | Compare papers | Select papers and dimensions → matrix with evidence per cell → comparability labels | MVP-1 |
| W6 | Review reproducibility checklist | Open checklist → each item shows status and evidence → `needs_review` items listed | MVP-1 |
| W7 | Discover papers | Search → see metadata and availability → add to project → attach a document by manual upload | MVP-1 |
| W8 | Correct or verify an item | Human confirms, corrects or rejects extracted items | Future |
| W9 | Research-gap exploration, knowledge graph | — | Future |

---

## 8. Data and provenance requirements

### 8.1 Data requirements

| ID | Requirement |
|---|---|
| DR-001 | Every extracted item, answer citation and checklist entry is traceable to one or more passages, and from there to a document and a paper. (VS-1 answers are not persisted; their citations are traceable in the response and in saved evaluation run artifacts. See §8.2.) |
| DR-002 | Source text (passages) and machine-generated interpretations (items, answers, checklist statuses) are stored in separate tables joined by explicit relationships. |
| DR-003 | All entities use stable internal identifiers (UUIDs), independent of titles, filenames and DOIs. |
| DR-004 | Passage text is immutable. Changes to parsing create a new passage set under a new document or parse run (`OQ-006`), never an in-place edit. |
| DR-005 | Each record that depends on a tool stores the producer: parser name/version, model identifier, prompt version, run time. |
| DR-006 | Distinguish in the data: unknown (null), parse failed, extraction failed, not found, and verified absent. These must not collapse into one boolean or null. |
| DR-007 | Page and section values are nullable. "Unknown" is never stored as 0 or an empty string. |
| DR-008 | Source documents are never deleted automatically. Human corrections are never overwritten by machine re-runs. |
| DR-009 | Quotations are stored exactly as taken from the passage text. |

### 8.2 Entities and MVP representation

| Entity | MVP representation | Notes |
|---|---|---|
| Paper | Table `papers` (VS-1) | Normalised DOI nullable, unique when present. |
| Document | Table `documents` (VS-1) | One per distinct file hash. Status, failure reason, parser info, storage keys. |
| Section | Columns `section_title`, `section_path` on `passages` (VS-1) | A separate `sections` table only if Phase 1 shows hierarchy is needed for retrieval or display. |
| Passage | Table `passages` (VS-1) | Ordinal unique within a document. |
| Research claim / extracted item | Table `extracted_items` (Phase 7) | Types: `dataset`, `metric`, `limitation`; later more. Method and algorithm are item types, not separate tables, until needed. |
| Evidence | Table `evidence` (Phase 7) | Links an item to a passage with a quotation and verification status. |
| Dataset, Metric, Method | Item types (Phase 7); normalised tables only if cross-paper entity merging proves necessary | Merging "ImageNet" variants across papers is a hard problem and is deferred. |
| Reported result | Representation open (`OQ-008`) | Required fields: dataset, metric, value, split, conditions. |
| Reproducibility item | Table `reproducibility_items` (Phase 11) | Status plus evidence links. |
| User correction | Future | Reserve verification status values; no table yet. |
| Embedding | Separate table (Phase 8, `AD-014`) | Keyed by passage and model. |
| Answer | Not persisted in VS-1 | Answers are API responses. The evaluation harness saves answers as run artifacts with model, retrieved passage IDs and configuration (`FR-EVL-003`). A table is added only when a requirement needs stored answers. Decided at P0-T1 review, 2026-11-03. |

### 8.3 Repeated ingestion, duplicates, updates and failures

| Situation | Required behaviour |
|---|---|
| Identical file uploaded again | No new document; the existing document is returned. No duplicate passages. |
| Different file, same DOI | New document under the same paper; both retained. Which is "primary" is future. |
| No DOI available | A new paper is created. Probable-duplicate detection is a later feature (`FR-DIS-002`, `OQ-007`). |
| Parser failure | Document `failed` with reason; no passages; retry permitted; original file retained. |
| Parser upgrade or re-parse of the same file | Not supported in VS-1. Before extraction (Phase 7) the policy must be decided because evidence links point at passage IDs (`OQ-006`). |
| Process crash during parsing | Recovered by `FR-ING-010`. |

---

## 9. AI and evidence integrity

### 9.1 Answer contract (proposed; finalised in Phase 5)

| Field | Meaning |
|---|---|
| `statements[]` | Each has `text` and `citations[]` (at least one). Citation = passage alias plus an optional exact quotation. Statement-level granularity makes claim-support labelling possible. Empty when `evidence_sufficiency` is `insufficient`. |
| `evidence_sufficiency` | `sufficient`, `partial` or `insufficient`. |
| `limitations` | Optional text about uncertainty or what was not found. |

System-added fields: `validation_status` (`validated`/`failed`), per-citation `valid` plus reason code, `retrieved_passage_ids`, `passages_dropped` (`FR-QA-002`), `retrieval_method`, `model`, `claim_support` (`not_evaluated`).

### 9.2 Rules

1. **Structured outputs, validated.** No free-text answers accepted in place of the contract.
2. **Citation identifier validation.** Aliases must resolve to retrieved passages (`FR-CIT-001`).
3. **Paper ownership validation.** A cited passage must belong to a paper in the question's scope.
4. **Quote and location verification** where technically possible (`FR-CIT-002`, `FR-CIT-003`). Limits: PDF extraction artifacts (hyphenation, ligatures, encoding) can make exact matching fail on true quotes (`OQ-013`).
5. **Insufficient evidence** is a first-class answer (`FR-QA-004`).
6. **Claim support is not claimed by deterministic checks.** A valid citation to a passage that does not support the statement passes `FR-CIT-001`. This is a known limitation, measured by `FR-EVL-004`, and `claim_support` stays `not_evaluated`.
7. **Human review** is required where automation cannot decide: claim support, `needs_review` checklist items, ambiguous comparability.

---

## 10. Evaluation strategy

| Component | Metric | How measured | What it can and cannot tell you |
|---|---|---|---|
| Parsing | Manual inspection checklist per sample paper: sections present, paragraphs intact, page info present, headers/footers leaking | Phase 1 reviewer notes | Descriptive only; not a score. |
| Retrieval | Recall@5 (`FR-EVL-002`) | About 20 reviewed questions with expected supporting quotes | Whether the right passage reaches the top 5. Small sample: differences between methods are indicative, not statistically conclusive. |
| Citation reference validity | validated ÷ total answers or citations | Harness over evaluation answers, plus fault-injection tests | Structural correctness only. |
| Claim support | supported ÷ labelled statements | Human labels with a written guide | Semantic correctness on the sampled statements. Needs sample size and labeller recorded. |
| Extraction | Precision, recall, F1 | Hand-labelled papers with a written matching rule | Depends on label quality and matching rule. |
| Comparison | Correctness of fields and of comparability labels | Small hand-verified set | Whether context is preserved. |
| Reproducibility | Classification accuracy per status | Hand-labelled items | Agreement with a labeller, not with scientific truth. |
| Duplicate detection | Precision and recall | Only if fallback matching is built | — |

Rules: the evaluation set exists before tuning. The same questions and ground truth are used when comparing methods. Baselines are recorded before any target is set. No result is reported unless it was produced by a run that is saved with date, code revision and configuration.

---

## 11. Risks and limitations

| ID | Risk | Mitigation |
|---|---|---|
| RISK-01 | Poor-quality, scanned or malformed PDFs | Detect and fail with a reason; no OCR in MVP. Phase 1 tests such files. |
| RISK-02 | GROBID fails, returns partial structure, or is unavailable | Explicit statuses (`FR-ING-003`); raw output retained; Phase 1 documents behaviour. |
| RISK-03 | Wrong passage boundaries (headers/footers, split paragraphs, tables) | Inspect in Phase 1; passage-quality checks; evaluate with Recall@5. |
| RISK-04 | Missing or unreliable page information | Page nullable; "unknown" shown; no invented pages. |
| RISK-05 | LLM hallucination | Structured output, deterministic validation, insufficient-evidence path, human-labelled claim support. |
| RISK-06 | Valid citation, unsupported claim | Explicit `claim_support: not_evaluated`; offline human-labelled measurement. |
| RISK-07 | Dataset or metric comparability errors | Deterministic comparability labels; no ranking unless `directly_comparable`. |
| RISK-08 | Prompt injection through paper text | Passages delimited as data; no tools or side effects available to the model; output validated by code. Not a complete defence. |
| RISK-09 | External API limits or changes (OpenAlex, LLM provider, GROBID) | Verify docs before implementing; timeouts; distinct error states. |
| RISK-10 | Provider cost and availability | Provider-independent interface; fake provider in tests; cost per answer recorded as a baseline. |
| RISK-11 | Incomplete evidence presented as complete | Sufficiency field; `partial` status; wording rules. |
| RISK-12 | False confidence in reproducibility assessments | No verdict or score; wording of `not_found`; `needs_review` for incomplete parses. |
| RISK-13 | Copyright and permission for uploaded papers | Users upload only papers they may use; document in `README.md`; no automatic bulk downloading. |
| RISK-14 | Scope creep from AI-generated code | Small tasks, approved scope, review (see `CLAUDE.md`). |
| RISK-15 | Evaluation set too small or biased | Record its limits with every result; grow it deliberately. |

---

## 12. MVP definition and acceptance

### 12.1 Vertical slice VS-1

> Upload one permitted research paper PDF → parse it using GROBID → store the document and passages in PostgreSQL → retrieve relevant passages using keyword search → answer a question using retrieved evidence → validate the returned citation references.

**Included requirements:** `FR-ING-001` to `FR-ING-010`, `FR-RET-001` to `FR-RET-004`, `FR-QA-001` to `FR-QA-007`, `FR-CIT-001` to `FR-CIT-005`, `FR-EVL-001` to `FR-EVL-004`, `FR-UI-001` to `FR-UI-003`, and the NFRs above.

**Acceptance criteria**

| ID | Criterion (observable) |
|---|---|
| AC-VS-01 | A valid PDF can be uploaded; the document reaches `parsed` or `failed`, never stuck. |
| AC-VS-02 | For at least three real papers, the structure view shows ordered passages with section and page-or-unknown, and the author has recorded manual observations. |
| AC-VS-03 | Invalid file, empty file, truncated PDF, GROBID unreachable and empty-parse cases each produce `failed` with the documented reason and no passages. |
| AC-VS-04 | Uploading the same file twice produces one document and one passage set. |
| AC-VS-05 | Keyword retrieval returns scoped, ranked passages; no-match returns an empty list. |
| AC-VS-06 | A question answerable from the paper returns statements with citations that all validate. |
| AC-VS-07 | A question the paper cannot answer returns `insufficient` and no confident factual statement. |
| AC-VS-08 | Fault-injection tests pass: nonexistent passage ID, passage from another paper, passage outside the context, malformed model output, altered quote, a statement without a citation in a sufficient or partial answer, an `insufficient` answer that contains statements. |
| AC-VS-09 | Recall@5 has been computed on the evaluation set and the recorded result file exists. (The value is reported, not required to meet a threshold.) |
| AC-VS-10 | `progress.md` records the verification evidence for each of the above, with dates. |

**Definition of done for VS-1:** all AC-VS items satisfied with evidence; migrations apply cleanly to an empty database; tests run from a documented command; `README.md` states how to run GROBID, PostgreSQL, backend and frontend; known limitations are written down.

### 12.2 MVP-1

VS-1 (accepted at the end of Phase 6, which completes its evaluation requirements) plus Phases 7–11 (`docs/implementation-roadmap.md`) and the release-readiness gate (milestone M14). Adoption of semantic or hybrid retrieval as the default is conditional on recorded evaluation.

### 12.3 After the MVP

Human correction workflow, knowledge graph, research-gap exploration (as hypotheses only), code repository analysis (static), stronger claim-support evaluation, asynchronous workers, object storage, authentication, deployment.

---

## 13. Open questions register

| ID | Question | Resolve by | Needed before |
|---|---|---|---|
| OQ-001 | How reliable are GROBID's section hierarchy and page/coordinate information on real papers? | **Answered 2026-11-03** (`docs/experiments/grobid-feasibility.md` §7): every body paragraph and heading had a page from GROBID coordinates (242/242 on five papers); store `page_start` and `page_end`. Sections are always flat; no `sections` table. | Phase 2 schema |
| OQ-002 | What passage granularity works (paragraph vs larger/smaller)? | **Provisional 2026-11-03** (`docs/experiments/grobid-feasibility.md` §7): paragraph passages plus two repair rules (see `AD-004`). Confirm with Recall@5 in Phase 4. | Phase 3 passage creation |
| OQ-003 | Are references stored (structured or raw only)? Are bibliography entries excluded from retrieval? | **Answered 2026-11-03** (`docs/experiments/grobid-feasibility.md` §7): GROBID returns structured and raw references separately from body text. References are not passages in VS-1; they stay in the stored raw TEI. Whether non-reference back matter (appendix, data availability, funding) becomes passages is decided in P1-T7. | Phase 3 |
| OQ-004 | FTS language configuration and query function (e.g. `english` vs `simple`; `websearch_to_tsquery` vs others). Ranking function and its limits. | Phase 4 experiment on the evaluation set | Phase 4 |
| OQ-005 | Upload size limit default. | **Answered 2026-11-03** (`docs/experiments/grobid-feasibility.md` §7): default 50 MB, configurable. Real papers were 0.09–1.85 MB; GROBID has no size limit and rejects over-long documents with `TOO_MANY_TOKENS`. | Phase 3 |
| OQ-006 | Re-parse policy: how to keep evidence links valid when passages are regenerated. | Design review | Phase 7 |
| OQ-007 | Paper matching when DOI is absent. | Phase 9 experiment | Phase 9 |
| OQ-008 | Representation of reported results (table, JSON, typed items). | Design review with hand-built examples | Phase 10 |
| OQ-009 | Extraction strategy for long documents; extraction-matching rule for scoring. | Phase 7 experiment | Phase 7 |
| OQ-010 | Initial reproducibility checklist items. | Hand-label 3 papers | Phase 11 |
| OQ-011 | LLM provider and model for answers and extraction (cost, structured-output support). | Short comparison on the evaluation set | Phase 5 |
| OQ-012 | Embedding model, dimension, pgvector index choice and limits. Verify limits in pgvector docs. | Phase 8 | Phase 8 |
| OQ-013 | Quote normalisation rules for PDF text artifacts. | **Provisional 2026-11-03** (`docs/experiments/grobid-feasibility.md` §7): verify quotes against stored passage text, never the PDF text layer. Rules: Unicode NFKC, ligatures, quote and dash folding, whitespace, split ligatures inside words. Test in P5-T6. | Phase 5 |
| OQ-014 | Tooling: Python packaging/dependency tool, linter/formatter, type checker, test runner, frontend package manager and UI library, SQLAlchemy/driver versions. (Earlier videos used uv, pnpm, pytest and ruff [T]; none is mandated here.) | **Resolved 2026-11-03** (`progress.md` §6.8): Python 3.14 via uv, pytest, ruff, mypy, SQLAlchemy 2.1 + Alembic + psycopg 3; frontend Vite + React + TypeScript with pnpm, no component library or animation library chosen yet (P3-T9). | Phase 0 |
| OQ-015 | GROBID image/tag, resource needs, and which model variant to use; PostgreSQL image that can later enable pgvector. | **Resolved 2026-11-03** (`progress.md` §6.8): `grobid/grobid:0.9.1-crf` (CPU, about 0.5 GB, needs about 4 GB RAM for full text); `pgvector/pgvector:0.8.7-pg18-trixie` (PostgreSQL 18, extension not enabled until Phase 8). Both bound to 127.0.0.1 only. | Phase 0 |
| OQ-016 | Whether tables and figures need handling in the MVP; whether tracing tooling is needed beyond structured logs. | **Deferred 2026-11-03** (`docs/experiments/grobid-feasibility.md` §7): table cells are not reliable enough to cite in VS-1; revisit in Phase 7. Whether captions become passages is decided in P1-T7. Tracing: revisit at Phase 6. | Phase 3 / Phase 6 |
| OQ-017 | Local runtime feasibility for `AD-015`: the developer's machine has no Docker or WSL2 and about 18 GB free on C:. Disk and memory needs of the chosen GROBID image must fit. | **Resolved 2026-11-03** (`progress.md` §6.8): WSL2 + Docker Desktop installed by the developer with `--installation-dir` and `--wsl-default-data-root` on E:, so images do not use C:. Installation verified 2026-11-03 (engine running, data disk on E:, `hello-world` succeeded). | Phase 0 (P0-T3) |

---

## Appendix A: Source basis, conflicts and unsupported assumptions

### A.1 What the transcript notes actually support

The earlier notes (`notes/architecture-notes-*.md`, `implementation-notes.md`, `claude-code-workflow.md`, `knowledge-gaps.md`) describe two videos. The videos did **not** involve GROBID, OpenAlex, scholarly papers, cross-paper comparison or reproducibility. Patterns used here:

| Pattern | Where it appears in the notes | How used here |
|---|---|---|
| SQLAlchemy models + Alembic migrations | fullstack video, step A5 | `AD-012` |
| Hybrid keyword + vector retrieval with RRF | fullstack A13, Claude Code B8 | Phase 8 as an *evaluated option* |
| Structured grounded answer with citation-ID validator and insufficient-evidence path | fullstack A14 | `FR-QA-*`, `FR-CIT-*` (author's validator logic was not fully described) |
| Test one document before a full ingestion batch | fullstack A12 | Phase 3/7 practice |
| Content-hash record manager to avoid duplicates | Claude Code B7 | `FR-ING-008` |
| Plan → save → clear → build → verify → commit; progress file for handoff; lean CLAUDE.md | Claude Code workflow notes | `CLAUDE.md`, `progress.md` |
| Table extraction was the largest quality problem | fullstack A10/A17 | `RISK-03`, `OQ-016` |

### A.2 Conflicts and resolutions

| Conflict | Resolution |
|---|---|
| Videos used Supabase (auth, RLS, storage, realtime). The project asks for plain PostgreSQL, local files, no auth. | Project definition wins (`AD-002`, `AD-009`). |
| Videos used Docling. The project prefers GROBID. | GROBID is the initial parser; Docling only as a fallback if Phase 1 justifies it (`AD-003`). |
| Fullstack video used an agent tool loop. The project asks for a simple inspectable pipeline. | Single-pass RAG (`AD-006`). |
| Earlier implementation roadmap (notes) placed embedding-dimension choice before the first slice and tracing before tools. | Moved: embeddings are Phase 8 (`AD-014`, `OQ-012`); tracing is not required (`AD-016`). |
| Notes' status wording ("not started / in progress / completed"). | Replaced by `not_started`, `in_progress`, `blocked`, `completed`. |
| Notes proposed a 26-step roadmap. | Replaced by the phase structure in `docs/implementation-roadmap.md`. |

### A.3 Unsupported or unverified assumptions

- ~~That GROBID gives usable page numbers and section structure (`OQ-001`).~~ Checked in Phase 1 on five papers: pages yes, sections flat (`docs/experiments/grobid-feasibility.md`).
- Pgvector index limits quoted in the notes came from a third-party summary and have not been checked against the pgvector documentation (`OQ-012`).
- GROBID endpoint and option details in the notes came from a documentation branch rather than the current stable pages (`OQ-015`).
- Any specific model, model price, or latency mentioned in the videos is the speaker's statement about one setup and does not predict PaperPilot's behaviour.
- Timeouts and top-k values are placeholders until measured. The upload limit (50 MB) is now based on Phase 1 measurements (`OQ-005`).
