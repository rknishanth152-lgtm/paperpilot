# PaperPilot: Implementation Roadmap

| Field | Value |
|---|---|
| Version | 0.2 (P0-T1 review changes applied 2026-11-03; see `progress.md` §6.7) |
| Date | 2026-11-03 |
| Implements | `PRD.md` (requirement, decision, question and risk IDs below refer to it) |
| Governed by | `CLAUDE.md` (how to work) |
| Actual state | `progress.md` (this file describes the *plan*; it never records what is done) |

The roadmap orders the work. It does not add or change requirements. If a phase needs something the PRD does not say, change the PRD first and note it in `progress.md`.

---

## 1. How to use this roadmap

1. Work one phase at a time, in the order below unless section 3 allows otherwise.
2. Inside a phase, work **one task at a time** (`P<phase>-T<n>`). A task is small enough to implement, test and review in one sitting. If a task cannot be described with a concrete check, split it.
3. A phase is finished only when every **exit criterion** has evidence recorded in `progress.md`. Generated code or a passing demo is not evidence by itself.
4. Statuses are `not_started`, `in_progress`, `blocked`, `completed`. Only `progress.md` holds them.
5. Where a phase begins with an experiment or an open question, the result may change later phases. Update this file and record why.
6. Test and command names are not given here. They are chosen in Phase 0 (`OQ-014`) and recorded in `README.md`.

### 1.1 Milestones and phases

| Milestone | Name | Phase | Release it belongs to |
|---|---|---|---|
| M1 | Requirements and architecture documentation | 0 | foundation |
| M2 | Repository and development environment setup | 0 | foundation |
| M3 | GROBID parsing experiment | 1 | VS-1 |
| M4 | Database schema and migrations | 2 | VS-1 |
| M5 | Paper ingestion and passage persistence | 3 | VS-1 |
| M6 | Keyword retrieval | 4 | VS-1 |
| M7 | Evidence-backed question answering | 5 | VS-1 |
| M8 | Evaluation harness | 6 | VS-1 (acceptance) |
| M9 | Structured extraction | 7 | MVP-1 |
| M10 | Semantic and hybrid retrieval | 8 | MVP-1 |
| M11 | Academic paper discovery | 9 | MVP-1 |
| M12 | Cross-paper comparison | 10 | MVP-1 |
| M13 | Reproducibility assessment | 11 | MVP-1 |
| M14 | Reliability and release readiness | cross-phase gate after Phase 11 | MVP-1 |
| — | Future extensions | 12 | not scheduled |

**VS-1 is functionally complete at the end of Phase 5** (the full chain works) and **accepted at the end of Phase 6**, once all `AC-VS-xx` criteria in the PRD have recorded evidence.

### 1.2 Task identifiers and size

`P3-T4` means task 4 of Phase 3. Task IDs are stable; if a task is split, use `P3-T4a`, `P3-T4b`. Tasks list the PRD IDs they implement.

### 1.3 Standing rules that apply to every phase

- Tests for the work are written in the same task as the code (`NFR-TST-001`, `NFR-TST-002`).
- Schema changes only through migrations (`NFR-MNT-002`).
- No secrets, no copyrighted PDFs, and no real API keys in the repository (`NFR-SEC-001`, `RISK-13`).
- External tools and APIs (GROBID, OpenAlex, pgvector, the LLM provider) are checked against their **current official documentation** before implementation. The result is recorded in the phase notes in `progress.md`, not assumed from earlier notes (`RISK-09`).
- Numbers for latency, cost and quality are baselines to be measured; no targets are invented (`NFR-PRF-001`).

---

## 2. Dependency map

```
Ph0 ─► Ph1 ─► Ph2 ─► Ph3 ─► Ph4 ─► Ph5 ─► Ph6 ═══ VS-1 accepted
 (Ph1 needs P0-T2, P0-T3,         │      │
  Python env)                     │      ├─► Ph7 ─► Ph10
                                  ├─► Ph8 (needs Ph4 baseline + Ph6 harness)
                       Ph9 (needs Ph2/Ph3; independent of Ph4-Ph8)
                       Ph11 (needs Ph3, Ph5 quote verification; benefits from Ph7)
   Ph7 + Ph8 + Ph9 + Ph10 + Ph11 ─► M14 gate ═══ MVP-1
```

| Phase | Hard prerequisites | Notes |
|---|---|---|
| 0 | none | Only P0-T2, P0-T3 and the Python environment from P0-T4 block Phase 1. P0-T1 (developer review) is required to complete M1 but is not a technical prerequisite for the GROBID experiment. |
| 1 | P0-T2, P0-T3, Python environment (P0-T4) | Findings change Phases 2 and 3. |
| 2 | 1 | |
| 3 | 2 | |
| 4 | 3 | Needs real parsed passages. |
| 5 | 4 | `OQ-011` decided at start. |
| 6 | 5 | |
| 7 | 5 (quote verification, answer-generation pattern), 6 (harness) | `OQ-006`, `OQ-009` decided at start. |
| 8 | 4, 6 | Cannot start without a recorded keyword baseline. |
| 9 | 2, 3 | May be done after Phase 6 in any order relative to 7 and 8. Must not delay VS-1. |
| 10 | 7 | `OQ-008` decided at start. |
| 11 | 3, 5, 6 | `OQ-010` decided at start. Using Phase 7 extraction as an input is optional. |
| M14 | 7–11 complete (or explicitly descoped in `progress.md`) | |

Order within 7, 8, 9 is flexible. Moving a phase earlier than its prerequisites is not.

### 2.1 Where each requirement group is delivered

| Group | Phase(s) |
|---|---|
| FR-ING-001..010 | 3 (FR-ING-008 constraints designed in 2) |
| FR-RET-001..004 | 4 |
| FR-RET-005..007 | 8 |
| FR-QA-001..007, FR-CIT-001..005 | 5 |
| FR-EVL-001, FR-EVL-002 | 4 |
| FR-EVL-003, FR-EVL-004 | 6 |
| FR-EVL-005 | 7 |
| FR-EVL-006 | 11 |
| FR-EVL-007 | 9 (only if fallback matching is built) |
| FR-EXT-001..006 | 7 |
| FR-DIS-001..005 | 9 |
| FR-CMP-001..004 | 10 |
| FR-REP-001..005 | 11 |
| FR-UI-001, FR-UI-002 | 3 |
| FR-UI-003 | 5 |
| NFR-* | enforced throughout; checked at M14 |

---

## Phase 0: Documentation and repository foundation (M1, M2)

**Objective.** Have agreed documents, a runnable local environment for PostgreSQL and GROBID, and basic conventions, with no more scaffolding than the next phase needs.

**Why needed.** The Phase 1 experiment needs GROBID running and a place for scripts and notes. Everything else benefits from the conventions fixed early (`AD-001`, `AD-015`).

**Prerequisites.** None.

**Tasks.**

| Task | Description | Blocks Phase 1? |
|---|---|---|
| P0-T1 | Developer reviews the four documents; triage `OQ-xxx`; fix wording or scope disagreements in the PRD. Record the review date in `progress.md`. | No (but closes M1) |
| P0-T2 | Initialise the repository (version control, `.gitignore` covering `.env`, local storage, virtual environments, build output, local data, and test PDFs), plus a minimal `README.md` stub. Create only the directories the next phases use (`scripts/`, `docs/`, `benchmarks/` as needed). | **Yes** |
| P0-T3 | Define the local runtime: Compose file for PostgreSQL and GROBID (`AD-015`). Verify current GROBID image name/tag, resource needs and health endpoint in the official docs (`OQ-015`); choose a PostgreSQL image that can later enable pgvector. GROBID must not be published beyond the local machine (`NFR-SEC-004`). Start both services and confirm GROBID responds. | **Yes** |
| P0-T4 | Choose and record tooling (`OQ-014`): Python version and dependency tool, linter/formatter, type checker, test runner, frontend package manager. Record them in `README.md` and `CLAUDE.md` section on commands. | Python environment only |
| P0-T5 | Add `.env.example` with placeholders for every setting known so far (database URL, GROBID URL, storage directory, upload limit, LLM provider placeholders). Configuration is loaded from the environment in one place. | No |
| P0-T6 | Create the minimal backend skeleton: application entry point with a health endpoint, configuration module, and one smoke test, to prove the test runner works. No domain code. | No |
| P0-T7 | Establish test conventions: `tests/unit`, `tests/integration`, `tests/evaluation`; a marker or equivalent that separates tests needing PostgreSQL/GROBID from pure tests; fake-provider approach stub is deferred to Phase 5. | No |
| P0-T8 | Create the minimal frontend skeleton only when Phase 3 begins; before that, verify the Node toolchain installs and builds an empty app if the developer wants early confidence. | No (may be deferred to Phase 3) |
| P0-T9 | Optionally add a CI workflow running the pure tests. Defer if it slows the learner (`.github/workflows/` exists in the target layout but is not required before Phase 6). | No |

**Expected files/components.** `.gitignore`, `README.md`, `docker-compose.yml`, `.env.example`, `backend/` skeleton, `tests/` skeleton, `scripts/`, `docs/`, the four planning documents.

**Testing and verification.**
- Compose starts PostgreSQL and GROBID; GROBID health/alive endpoint responds (command recorded in README).
- Health endpoint test passes using the chosen runner.
- `git status` shows `.env` and local data are not tracked (create a dummy `.env` to prove the rule works, then delete it).
- A secrets scan or manual grep of the first commit finds no credentials.

**Acceptance criteria.**
1. Documents reviewed; open-question triage recorded (M1).
2. A new clone plus README instructions reproduces: services running, backend smoke test passing (M2).
3. Tooling decisions recorded with dates.

**Definition of done.** Acceptance criteria met with evidence in `progress.md`; the minimal subset (T2, T3, Python environment from T4) is verifiably working even if other tasks are deferred.

**Risks and failure cases.** GROBID image is large or needs more memory than the machine has (`OQ-015`); port clashes; Docker unavailable on the developer's machine (then document native install as an alternative and re-examine `AD-015`); over-scaffolding.

**Deferred.** Frontend feature code, CI beyond a smoke job, database schema, authentication, deployment files, container images for the application itself.

---

## Phase 1: GROBID feasibility experiment (M3)

**Objective.** Learn, on real papers, what GROBID reliably gives (metadata, section structure, paragraphs, references, page information) and how it fails, and decide how the application will represent parser output. The experiment's result is knowledge; the code is disposable script code.

**Why needed.** `AD-003`, `AD-004` and the passage model rest on untested assumptions (`OQ-001`, `OQ-002`, `OQ-003`, `OQ-013`, `OQ-016`). Nothing in Phases 2 and 3 should be designed before this.

**Prerequisites.** P0-T2, P0-T3, Python environment.

**Tasks.**

| Task | Description |
|---|---|
| P1-T1 | Read the current GROBID service documentation for the full-text endpoint and options (consolidation, coordinates, sentence segmentation, response codes) and record what was confirmed. |
| P1-T2 | Select 3–5 permitted papers with varied structure: a standard two-column paper, a single-column paper, one with many tables, one long paper or one with unusual headings, and, if available, one with weak text extraction. Record title, source, and permission basis. **Do not commit the PDFs.** |
| P1-T3 | Write a throwaway script under `scripts/` that sends each paper to GROBID and saves the raw output (outside version control or in an ignored directory). Record response status and parse time per paper. |
| P1-T4 | Inspect each output against a fixed checklist: title, authors, abstract, DOI present; section headings and nesting; paragraphs intact or split; header/footer/page-number text leaking into paragraphs; references; figures and tables handling; availability and form of page/coordinate information. Note whether the text can be matched back to the PDF text for quote verification. |
| P1-T5 | Failure tests: non-PDF bytes with `.pdf` name, empty file, truncated PDF, a scanned/image-only PDF if one is permitted, GROBID stopped while a request is in flight or unreachable, a very large file. Record response codes, errors and timings. |
| P1-T6 | Write `docs/experiments/grobid-feasibility.md`: setup used, papers (by title/identifier), per-paper observations, failure behaviour, limitations, and **explicit answers or deferrals** for `OQ-001`, `OQ-002`, `OQ-003`, `OQ-005`, `OQ-013`, `OQ-016`. |
| P1-T7 | Decide the internal representation of parser output (what fields the ingestion module expects: metadata, ordered sections, paragraphs with optional page and coordinates) and write it down. This is a design note, not an implementation. |
| P1-T8 | Record a go / go-with-limits / no-go decision. If **no-go**, define a bounded follow-up experiment with the fallback parser (`AD-003`) and update the PRD; do not silently switch. |

**Expected files.** `scripts/` experiment script, `docs/experiments/grobid-feasibility.md`. No application code.

**Testing and verification.** The experiment is itself the verification. Reproducibility check: the report lists the exact steps and the GROBID version/tag used so the run can be repeated.

**Acceptance criteria.**
1. At least 3 papers processed; raw outputs inspected against the checklist.
2. At least the six failure inputs above attempted (or explicitly impossible, with the reason).
3. Report states observed limitations, answers/deferrals for the listed open questions, a go/no-go decision, and the parser-output representation.
4. No claim in the report is untested: unobserved behaviour is marked unknown.

**Definition of done.** Report committed and linked from `progress.md`; PRD updated where findings change it (passage definition, status reasons, upload limit).

**Risks and failure cases.** GROBID gives no usable page data (then page is "unknown" and `FR-CIT-003` relies on section only; PRD already allows this); paragraph boundaries are poor (reconsider `AD-004`); headers/footers leak (add cleaning rules); too small a sample to generalise (record the sample limits); documentation and observed behaviour disagree (trust observation, record the discrepancy).

**Deferred.** Persisting anything; evaluating alternative parsers (unless go decision is no-go); table/figure extraction quality beyond noting behaviour; OCR.

---

## Phase 2: Core persistence and provenance (M4)

**Objective.** The smallest useful relational schema (`papers`, `documents`, `passages`) with migrations, stable identifiers, status fields and uniqueness rules that make repeat ingestion safe.

**Why needed.** Every later feature links to passages (`DR-001`, `DR-003`). Correct constraints now avoid data repair later.

**Prerequisites.** Phase 1 complete (representation and status reasons known).

**Tasks.**

| Task | Description |
|---|---|
| P2-T1 | Write the schema design note: columns, types, nullability (page and section nullable per `DR-007`), constraints, enumerations (document statuses `pending`, `processing`, `parsed`, `failed`; `failure_reason` codes from Phase 1), indexes. Settle whether a paper may have several documents (PRD: yes). |
| P2-T2 | Set up the database access layer and migration tool (`AD-012`, `OQ-014`): configuration, session handling, migration environment. |
| P2-T3 | Create the first migration for `papers`, `documents`, `passages`: UUID primary keys (`DR-003`); `documents.sha256` unique; normalised DOI unique when present; passage ordinal unique per document; foreign keys; check constraints for status values. |
| P2-T4 | Implement DOI normalisation as a pure, tested function (case, `https://doi.org/` and `doi:` prefixes, whitespace). |
| P2-T5 | Write constraint-focused integration tests against a real PostgreSQL: migration applies to an empty database and can be inspected; duplicate hash rejected; same DOI two documents allowed under one paper; foreign-key violation rejected; invalid status rejected; passage ordinal duplicate rejected; null page stored and read back as null (not 0). |
| P2-T6 | Document the schema in `docs/` (short: tables, constraints, rationale) and update `progress.md`. |

**Expected files.** Models, migration files, database/config module, `tests/integration` schema tests, schema note.

**Testing and verification.** Integration tests above, run against the Compose PostgreSQL; migrations applied to a freshly created empty database in the same run.

**Acceptance criteria.**
1. Migration applies cleanly to an empty database.
2. Each constraint listed in P2-T5 has a failing-case test that passes.
3. Repeat-ingestion rules of PRD section 8.3 are expressible in the schema (tests show unique hash and shared-DOI behaviour).
4. Passage text immutability is a code convention documented in `CLAUDE.md` (database-level enforcement is optional and decided in the design note).

**Definition of done.** Acceptance criteria evidenced; no tables beyond the three; schema note written.

**Risks and failure cases.** Schema guessed before Phase 1 (do not proceed if Phase 1 isn't done); a driver/dialect mismatch in the connection URL (record the working configuration); over-modelling (sections table, entities) added without need.

**Deferred.** `extracted_items`, `evidence`, `reproducibility_items`, embeddings, users, a separate `sections` table, full-text search column (Phase 4), re-parse versioning (`OQ-006`, decided before Phase 7).

---

## Phase 3: End-to-end ingestion (M5)

**Objective.** A user can upload a PDF, see it processed by GROBID, stored as a paper/document/passages, and inspect the result, with every failure visible as a status and never as a misleading success.

**Why needed.** It is the first half of the vertical slice and the source of all evidence.

**Prerequisites.** Phase 2; Phase 1 representation decision.

**Tasks.**

| Task | Description | Requirements |
|---|---|---|
| P3-T1 | Storage interface (save/read/delete by key) with local-filesystem implementation; generated keys; tests for key generation, path traversal attempts, write failure. | FR-ING-002, NFR-SEC-002, AD-002 |
| P3-T2 | Upload validation: PDF signature check, empty file, size limit from configuration, filename handling (`OQ-005` default from Phase 1). | FR-ING-001 |
| P3-T3 | GROBID client wrapper: timeout from configuration, mapping of HTTP/transport errors (including 204 and 503) to `failure_reason` codes; unit tests with a stub server; one integration test with real GROBID. | FR-ING-004, FR-ING-003, NFR-REL-003 |
| P3-T4 | TEI → internal representation → metadata and passages (pure function over the saved XML); tests on stored small TEI fixtures. Normalisation rules from Phase 1. Bibliography excluded from retrievable passages unless Phase 1 decided otherwise. | FR-ING-005, FR-ING-006, FR-ING-007 |
| P3-T5 | Ingestion orchestration: create document `pending`, set `processing`, run parse, store raw artifact, persist paper/passages in one transaction, set `parsed` or `failed`. A document with zero passages is `failed` (`empty_parse`). | FR-ING-003, FR-ING-005 |
| P3-T6 | Duplicate and retry behaviour: identical hash returns existing document; same DOI new document under same paper; retry for `failed`; no duplicate passages on retry or concurrent identical uploads. | FR-ING-008, NFR-REL-002 |
| P3-T7 | Startup recovery of stale `processing` documents → `failed/interrupted`. Test with a manufactured stale row. | FR-ING-010, AD-010 |
| P3-T8 | HTTP API: upload, status, structure view. Structured error responses without internals. | FR-ING-009, NFR-SEC-005 |
| P3-T9 | Minimal frontend: upload form, status display with failure reason, structure view (metadata, sections, passages, page or "unknown"). Create the frontend skeleton here if not yet done (`P0-T8`). | FR-UI-001, FR-UI-002, NFR-ACC-001, NFR-UX-001 |
| P3-T10 | Manual run on at least three real permitted papers (the Phase 1 set is fine); record observations in `progress.md`. Update `README.md` run instructions. | AC-VS-01, AC-VS-02 |

**Expected files/components.** `backend/app/services/ingestion/`, storage module, `api/` routes, `schemas/`, GROBID client, `frontend/` upload and structure pages, TEI fixtures (small, license-safe or synthetic), `tests/unit`, `tests/integration`.

**Testing and verification.**
- Unit: validation, key generation, TEI parsing on fixtures, normalisation, error-code mapping.
- Integration: end-to-end ingestion with real GROBID and PostgreSQL on at least one sample; stub-server failure scenarios; duplicate upload; interrupted-processing recovery.
- Failure matrix (`FR-ING-003`): invalid file, empty file, truncated PDF, GROBID unreachable, GROBID 503, malformed XML, empty parse each results in `failed` with the correct reason and **zero passages**.
- Manual: UI shows each state distinctly.

**Acceptance criteria.** `AC-VS-01`, `AC-VS-02`, `AC-VS-03`, `AC-VS-04` from the PRD, plus: no `parsed` document has zero passages; original file hash equals recorded hash.

**Definition of done.** All acceptance criteria evidenced in `progress.md`; tests runnable with the documented command; README explains how to run the pieces.

**Risks and failure cases.** Long parse blocks the request (`AD-010`: use status polling; measure parse times first); GROBID returns partial structure that looks valid (inspect passages, not just status); concurrency creating duplicate rows (rely on the unique constraint and handle the conflict); log leakage of paper text (`NFR-PRI-002`).

**Deferred.** Queue/workers, re-parse of an existing file (`OQ-006`), OCR, table/figure extraction, bulk upload, deletion of documents, authentication.

---

## Phase 4: Keyword retrieval (M6)

**Objective.** Passage retrieval using PostgreSQL full-text search, plus a manually reviewed evaluation set and a recorded Recall@5 baseline.

**Why needed.** Establishes the baseline against which every later retrieval change is judged (`AD-005`, `FR-EVL-002`).

**Prerequisites.** Phase 3 with at least three parsed real papers.

**Tasks.**

| Task | Description | Requirements |
|---|---|---|
| P4-T1 | Check the current PostgreSQL full-text search documentation for query-parsing functions, ranking functions and language configurations; record the chosen configuration and the reasons (`OQ-004`). | FR-RET-001, FR-RET-003 |
| P4-T2 | Migration adding the search representation for passages and the supporting index; confirm new passages are searchable without a manual step. | FR-RET-001, NFR-MNT-002 |
| P4-T3 | Retrieval function: scope by paper/document, only `parsed` documents, limit `k`, deterministic tie-breaking, parameterised query, no exception on arbitrary input. Not coupled to any LLM code. | FR-RET-002, FR-RET-003, FR-RET-004 |
| P4-T4 | Tests: no match → empty list; punctuation-only and empty query; SQL-like and operator-like input; scope isolation (passages of another paper never returned); deterministic order. | FR-RET-002, FR-RET-003 |
| P4-T5 | Build the evaluation set in `benchmarks/`: about 20 questions over at least 3 papers; for each, expected supporting quote(s) and paper, answerable or not; some unanswerable questions; reviewer and date recorded. Written **before** looking at retrieval output for those questions. | FR-EVL-001 |
| P4-T6 | Evaluation harness v0 for retrieval only: maps expected quotes to passage IDs at run time, computes Recall@5, lists hits, misses and unmatched expectations, saves a dated result file with code revision and configuration (stored under `benchmarks/`; harness code under `tests/evaluation/`). | FR-EVL-002 |
| P4-T7 | Run the baseline, analyse every miss (query wording, passage boundary, vocabulary mismatch, labelling error), record findings. Adjust passage rules or query handling only with the evaluation set held fixed, and record before/after. Revisit `OQ-002`. | FR-EVL-002 |

**Expected files.** `backend/app/services/retrieval/`, migration, `benchmarks/` dataset and result files, `tests/evaluation/` harness, retrieval API route (if needed by the UI later).

**Testing and verification.** Unit/integration tests above; harness run recorded.

**Acceptance criteria.** `AC-VS-05`; the evaluation set meets `FR-EVL-001`; Recall@5 baseline recorded (value is reported, no threshold required); every miss has a recorded cause.

**Definition of done.** Evidence in `progress.md`; `OQ-004` resolved or explicitly documented as an interim choice.

**Risks and failure cases.** Evaluation labelling errors inflate or deflate scores; the set is small (state its limit with every result; `RISK-15`); tuning to the evaluation set (hold it fixed, do not edit questions after seeing results without logging it); wrong language configuration hurting recall for technical terms.

**Deferred.** Vectors, reranking, query expansion by LLM, synonym dictionaries, highlight/snippet UI.

---

## Phase 5: Evidence-backed question answering (M7)

**Objective.** The full chain: question → retrieval → bounded context → one structured LLM response → citation validation → final answer with visible validity.

**Why needed.** It completes the VS-1 chain and implements the evidence-integrity rules (`AD-006`, `AD-007`, `AD-008`).

**Prerequisites.** Phase 4.

**Tasks.**

| Task | Description | Requirements |
|---|---|---|
| P5-T1 | Decide provider and model for answers (`OQ-011`) using current provider documentation (structured-output support, privacy terms, cost); record the decision, including how paper text is shared (`NFR-PRI-001`). | OQ-011 |
| P5-T2 | Model interface plus **fake implementation**; configurable timeout; error mapping (timeout, rate limit, authentication) to explicit errors. | FR-QA-005, AD-011 |
| P5-T3 | Answer schema (Pydantic) from PRD 9.1: statements, citations (alias + optional quote), sufficiency, limitations. Reject extra or missing fields. | FR-QA-003 |
| P5-T4 | Context builder: top-k passages, aliases, labels, deterministic truncation with `passages_dropped`, passage text delimited as data, instructions placed outside the data. | FR-QA-002, FR-QA-007 |
| P5-T5 | Prompt and call: one retrieval, one model call; retry policy for malformed output documented and bounded; no agent loop. | FR-QA-001, FR-QA-003, AD-006 |
| P5-T6 | Quote normalisation and matching (pure functions) using Phase 1 samples (`OQ-013`). | FR-CIT-002 |
| P5-T7 | Citation validator: alias resolution; existence; paper in scope; in context; quote presence; reason codes (`passage_not_found`, `wrong_paper`, `not_in_context`, `quote_mismatch`); `validation_status` per FR-CIT-004. | FR-CIT-001..004 |
| P5-T8 | Insufficient-evidence paths: empty retrieval skips the model; the model's `insufficient` is preserved and not decorated with citations. | FR-QA-004 |
| P5-T9 | Final response assembly: statements, per-citation validity, evidence passages with page/section **from the database**, `retrieved_passage_ids`, `retrieval_method`, `model`, `claim_support: not_evaluated`. | FR-QA-006, FR-CIT-003, FR-CIT-005 |
| P5-T10 | Fault-injection tests with the fake model: nonexistent passage ID; passage from another paper; passage not in context; malformed JSON; extra/missing fields; altered quote; wrong model-supplied page; statement without a citation in a sufficient or partial answer; insufficient answer that contains statements; passage text containing an instruction; provider timeout. | AC-VS-08, NFR-TST-002 |
| P5-T11 | API route and UI: question box, answer statements, citation validity indicators (text plus icon, not colour only), evidence panel, visible failed-validation state. | FR-UI-003, NFR-ACC-001, NFR-UX-001 |
| P5-T12 | Manual run with the real model on the evaluation questions: record answerable and unanswerable cases, any failed validations, cost and latency per answer as baselines. | AC-VS-06, AC-VS-07, NFR-PRF-001 |

**Expected files.** `backend/app/services/` QA/answer module (placed with retrieval or a new `answering` module; record the choice), `schemas/`, model interface and fake, validator, frontend question view, `tests/unit` and `tests/integration` for the validator and pipeline.

**Testing and verification.** Fault-injection suite (all with the fake model, offline); integration test of the full chain with the fake model against a real database; a small, clearly labelled manual run with the real model. Deterministic checks are not claimed to prove claim support.

**Acceptance criteria.** `AC-VS-06`, `AC-VS-07`, `AC-VS-08`; `claim_support` always `not_evaluated`; a response with any invalid citation is marked `failed` and visibly not evidence-backed in the UI.

**Definition of done.** Evidence in `progress.md` including the manual run's raw observations; `OQ-011` and `OQ-013` resolved or marked interim.

**Risks and failure cases.** Valid-but-unsupportive citations pass the structural checks (`RISK-06`, measured in Phase 6); prompt injection (`RISK-08`); true quotes failing normalisation (`RISK-03`); model refuses or returns non-JSON; cost surprises; the model citing aliases outside the context.

**Deferred.** Streaming answers, conversation memory, multi-turn chat, agent loops, LLM-judge claim support, reranking, answer caching.

---

## Phase 6: Evaluation and reliability (M8)

**Objective.** Make evaluation repeatable and complete for VS-1: retrieval, citation reference validity and sampled claim support, with baselines recorded and failure-path tests for the main reliability risks.

**Why needed.** Without a repeatable harness, later changes (extraction, hybrid retrieval) cannot be judged (`FR-EVL-*`, `NFR-COR-002`).

**Prerequisites.** Phase 5.

**Tasks.**

| Task | Description | Requirements |
|---|---|---|
| P6-T1 | One command runs the retrieval evaluation (from P4) and the answer evaluation; results saved as dated run artifacts with code revision, configuration, model identifier and prompt version. Result files are never edited by hand. | FR-EVL-002, FR-EVL-003 |
| P6-T2 | Citation reference-validity rate over evaluation answers, with failure reasons. | FR-EVL-003 |
| P6-T3 | Claim-support labelling: write a labelling guide (supported / partly supported / not supported / cannot judge), draw a sample of statements, label them manually, record labeller and date, report the rate **with sample size**. | FR-EVL-004 |
| P6-T4 | Reliability tests: parse failures; database failure during ingestion (no half-committed state); repeated identical requests (idempotence); malformed model output; incomplete or missing evidence. | NFR-REL-001, NFR-REL-002, NFR-TST-002 |
| P6-T5 | Baseline report `docs/` or `benchmarks/`: Recall@5, validity rate, claim-support rate with sample size, latency and cost per answer, known limitations. **No targets are set from the first baseline alone**; any later target is a new decision recorded in the PRD. | NFR-PRF-001, RISK-15 |
| P6-T6 | VS-1 acceptance review against all `AC-VS-xx`; update `progress.md`; list remaining known limitations. | AC-VS-10 |

**Expected files.** `tests/evaluation/` harness, `benchmarks/` datasets, labels and result files, labelling guide, baseline report.

**Testing and verification.** Run the harness twice on unchanged code and confirm the retrieval result is identical (determinism); fault-injection and reliability tests green.

**Acceptance criteria.** `AC-VS-09`, `AC-VS-10`; all AC-VS items with evidence; claim-support sample size recorded.

**Definition of done.** VS-1 accepted by the developer; baseline report committed.

**Risks and failure cases.** Small samples give noisy rates (report them as indicative, `RISK-15`); the single labeller's bias; model nondeterminism making answer-level evaluation unstable (record model, temperature settings and run date; repeat runs if feasible).

**Deferred.** Automated claim-support judge, large benchmark sets, CI-run model evaluations, dashboards.

---

## Phase 7: Structured research extraction (M9)

**Objective.** Extract datasets, metrics and limitations, each with an evidence link and a deterministic quote check, and measure quality against hand-labelled papers.

**Why needed.** Comparison (Phase 10) and parts of the reproducibility checklist depend on trustworthy structured data (`FR-EXT-*`).

**Prerequisites.** Phases 5 and 6; `OQ-006` (re-parse policy) and `OQ-009` (long documents, matching rule) decided at the start.

**Tasks.**

| Task | Description | Requirements |
|---|---|---|
| P7-T1 | Resolve `OQ-006` and `OQ-009`; write the design note: tables `extracted_items` and `evidence`, run records, verification statuses (`unverified`, `quote_matched`, `quote_unmatched`, `human_confirmed`, `human_rejected` reserved), how long documents are processed. | FR-EXT-004, FR-EXT-005, AD-013 |
| P7-T2 | Migration and models for items, evidence and extraction runs. | NFR-MNT-002 |
| P7-T3 | Hand-label 3–5 papers for datasets, metrics, limitations; write the matching rule before scoring. | FR-EVL-005, OQ-009 |
| P7-T4 | Extraction prompt and Pydantic schema; one pipeline per item type; "none found" recorded as an outcome. | FR-EXT-001, FR-EXT-002 |
| P7-T5 | Deterministic quote verification reusing Phase 5 functions; unmatched items flagged `quote_unmatched`. | FR-EXT-003 |
| P7-T6 | Run records (model, prompt version, time); re-running preserves earlier runs and any human-confirmed item (test with a simulated confirmation). | FR-EXT-005 |
| P7-T7 | Fault-injection tests: malformed output, invented quote, item without evidence, schema violation. | FR-EXT-002, FR-EXT-003 |
| P7-T8 | Scoring: precision, recall, F1 against the labels; saved baseline result; error analysis. | FR-EVL-005, FR-EXT-006 |
| P7-T9 | Minimal review UI or API output listing items with their evidence and verification status. | PRD §5.10 note |

**Expected files.** `backend/app/services/extraction/`, schemas, migration, labelled data in `benchmarks/`, scoring harness.

**Testing and verification.** Fake-model unit tests; integration tests for persistence; scoring run saved as an artifact.

**Acceptance criteria.** `FR-EXT-001..006` acceptance criteria; baseline P/R/F1 recorded before any downstream use; no extracted text is written into `passages`.

**Definition of done.** Evidence in `progress.md`; known limitations (entity naming variants, long documents) written down.

**Risks and failure cases.** Hallucinated items with plausible quotes (quote check is necessary but not sufficient); the model paraphrasing instead of quoting; variant names for the same dataset not matched (normalisation deferred); long documents exceeding the context; labelling disagreement.

**Deferred.** Cross-paper entity merging, methods/algorithms/hyperparameters extraction, tables-as-data extraction (until `OQ-016` supports it), human correction workflow (statuses reserved only).

---

## Phase 8: Semantic and hybrid retrieval (M10)

**Objective.** Add embeddings and pgvector and compare keyword, semantic and hybrid retrieval on the same evaluation set, adopting a new default only on evidence.

**Why needed.** Keyword search may miss paraphrases; whether vectors help on this corpus is an empirical question (`FR-RET-007`).

**Prerequisites.** Phase 4 baseline and Phase 6 harness.

**Tasks.**

| Task | Description | Requirements |
|---|---|---|
| P8-T1 | Resolve `OQ-012`: read current pgvector documentation (supported types, dimension limits for indexed and unindexed columns, index types, distance operators), and the embedding provider documentation; choose model and dimension; record. | OQ-012 |
| P8-T2 | Migration: enable the extension, create the embeddings table keyed by passage and model (`AD-014`), add the index chosen. | AD-014, NFR-MNT-002 |
| P8-T3 | Embedding interface with fake implementation; batch embedding job for existing passages; report passages missing embeddings. | FR-RET-005, AD-011 |
| P8-T4 | Semantic retrieval with the same scope and `k` semantics as keyword retrieval. | FR-RET-005 |
| P8-T5 | Hybrid retrieval: Reciprocal Rank Fusion implemented as one candidate; fallback to a single method with reporting when the other is unavailable. | FR-RET-006 |
| P8-T6 | Run all three on the unchanged evaluation set; record Recall@5 and per-question differences; analyse where each wins; record cost and latency. | FR-RET-007 |
| P8-T7 | Decide the default retrieval method from the recorded results, or keep keyword if the evidence does not justify a change. Update `progress.md` and the PRD decision table. | FR-RET-007 |

**Expected files.** `backend/app/services/retrieval/` additions, migration, embedding interface, comparison result files.

**Testing and verification.** Unit tests of fusion logic with fixed ranked lists; integration tests for vector search; dimension-mismatch and missing-embedding tests; recorded comparison.

**Acceptance criteria.** `FR-RET-005..007`; comparison recorded with the same questions and ground truth as the baseline.

**Definition of done.** Decision recorded with evidence; if semantic/hybrid is not better, that result is also recorded and the default stays keyword.

**Risks and failure cases.** Dimension or index limits (`OQ-012`); embedding cost for many passages; small evaluation set cannot separate close methods (say so); re-embedding when the model changes; extension not available in the chosen image.

**Deferred.** Reranking models, fine-tuned embeddings, query rewriting, multi-vector or late-interaction methods.

---

## Phase 9: Academic discovery (M11)

**Objective.** Search OpenAlex, normalise metadata, detect duplicates, and distinguish a paper record from an accessible document.

**Why needed.** Lets users find papers without leaving the application, without making discovery a dependency of ingestion (`FR-DIS-005`).

**Prerequisites.** Phases 2 and 3. Can run in parallel with Phases 7–8; must never delay VS-1.

**Tasks.**

| Task | Description | Requirements |
|---|---|---|
| P9-T1 | Read current OpenAlex documentation for work search and filter by DOI, the abstract format, authorship fields, open-access fields, rate/usage policy and authentication. Record confirmed facts and unknowns (`RISK-09`). | FR-DIS-001 |
| P9-T2 | Client with timeout and error mapping, distinguishing "no results" from "API error"; recorded fixtures for unit tests (no live calls in the default test run). | FR-DIS-001 |
| P9-T3 | Metadata normalisation: DOI normalisation reused from P2-T4, abstract reconstruction (nullable), authors, year, venue. | FR-DIS-002, FR-DIS-004 |
| P9-T4 | Duplicate detection by DOI; decide the fallback for papers without DOI (`OQ-007`), flagged as probable matches only. | FR-DIS-002 |
| P9-T5 | Availability states: metadata-only, landing page reported, direct PDF link reported; never claim a PDF is available or permitted. | FR-DIS-003 |
| P9-T6 | Adding a discovered paper creates a metadata-only paper; attaching a manually uploaded document to it works through the existing ingestion path. | FR-DIS-005 |
| P9-T7 | If fallback matching is built, measure its precision and recall on a hand-labelled set. | FR-EVL-007 |
| P9-T8 | Minimal API and UI to search and add. | — |

**Expected files.** `backend/app/services/discovery/`, schemas, fixtures, route and UI additions.

**Testing and verification.** Unit tests against recorded responses; DOI-form matching tests; error-state tests; one optional manual live check recorded in `progress.md`.

**Acceptance criteria.** `FR-DIS-001..005`; manual upload works with discovery disabled.

**Definition of done.** Evidence recorded; documentation of API assumptions that were verified versus not.

**Risks and failure cases.** Rate limits or API changes; OA URL being a landing page rather than a PDF; missing or inconsistent DOIs; inverted-index abstract reconstruction errors; accidental automatic download of papers (not allowed, `RISK-13`).

**Deferred.** Other discovery providers, citation-graph traversal, recommendation, automatic PDF fetching.

---

## Phase 10: Cross-paper comparison (M12)

**Objective.** Matrices of extracted information across papers that preserve experimental context, label comparability deterministically, and link every cell to evidence.

**Why needed.** Prevents misleading comparisons (`FR-CMP-003`, `RISK-07`).

**Prerequisites.** Phase 7; `OQ-008` decided at the start.

**Tasks.**

| Task | Description | Requirements |
|---|---|---|
| P10-T1 | Hand-build, for 3–4 papers, the expected comparison (including at least one pair that must be labelled not comparable, one with missing context). | FR-CMP-003 |
| P10-T2 | Decide and document the reported-result representation (`OQ-008`); extend extraction if required (dataset, metric, value, split, conditions, evidence). Update the PRD. | FR-CMP-004, OQ-008 |
| P10-T3 | Comparability rules as pure, documented, tested functions; labels `directly_comparable`, `requires_context`, `not_comparable`, `insufficient_information`. | FR-CMP-003 |
| P10-T4 | Matrix builder using only existing extracted items; absent cells shown `not_extracted`. | FR-CMP-001 |
| P10-T5 | Evidence on every cell; items with `quote_unmatched` excluded by default. | FR-CMP-002, FR-EXT-003 |
| P10-T6 | API/UI view of the matrix with labels and evidence. | FR-CMP-002 |
| P10-T7 | Compare outputs against the hand-built expected matrix; record discrepancies. | — |

**Expected files.** `backend/app/services/comparison/`, tests with hand-verified fixtures.

**Testing and verification.** Unit tests of comparability rules including the "different dataset never directly comparable" and "missing split → insufficient_information" cases; integration test over fixtures; manual verification against hand-built matrix.

**Acceptance criteria.** `FR-CMP-001..004` acceptance criteria; no ranking produced for non-comparable results.

**Definition of done.** Evidence recorded; comparability rules documented, including their known blind spots (dataset version differences, metric variants).

**Risks and failure cases.** Naming variants defeating matching; context spread across table captions not extracted (`OQ-016`); over-trusting extraction errors; users reading a matrix as a ranking.

**Deferred.** Automatic entity merging, statistical comparison, leaderboards, LLM-generated comparison prose.

---

## Phase 11: Reproducibility assessment (M13)

**Objective.** A limited, versioned checklist of experimental reporting items with the four statuses and evidence, with wording that never turns "not found" into "irreproducible".

**Why needed.** It is a core project capability (`FR-REP-*`, `RISK-12`).

**Prerequisites.** Phases 3, 5, 6; `OQ-010` decided at the start.

**Tasks.**

| Task | Description | Requirements |
|---|---|---|
| P11-T1 | Hand-assess 3 papers against a draft checklist (candidate topics in `FR-REP-001`); reduce to a small first version (`OQ-010`); document each item's definition and what counts as `reported`, `partially_reported`, `not_found`, `needs_review`. | FR-REP-001 |
| P11-T2 | Migration and models for assessments and items with checklist version, status, evidence links, material examined. | FR-REP-002, AD-013 |
| P11-T3 | Assessment pipeline: retrieval of relevant passages per item, structured model output, deterministic quote verification. | FR-REP-002, FR-REP-003 |
| P11-T4 | Rules: no verified evidence → cannot be `reported`/`partially_reported`; incomplete or failed parse → `needs_review`, never `not_found`. | FR-REP-002, FR-REP-003 |
| P11-T5 | UI/API wording review: no score, no verdict, `not_found` described as "not found in the material examined". | FR-REP-004, NFR-ACC-001 |
| P11-T6 | Fault-injection tests (status without evidence, fabricated quote, failed parse). | NFR-TST-002 |
| P11-T7 | Evaluate against the hand-labelled items; record per-status accuracy and confusion between `not_found` and `needs_review`. | FR-EVL-006, FR-REP-005 |

**Expected files.** `backend/app/services/reproducibility/`, checklist definition file, migration, labelled data.

**Testing and verification.** Fake-model tests for rules; scoring run saved.

**Acceptance criteria.** `FR-REP-001..005` acceptance criteria.

**Definition of done.** Evidence recorded; limitations stated (checklist is a reporting aid, not a judgement of scientific validity).

**Risks and failure cases.** Information reported in tables or supplements not captured (`OQ-016`, `RISK-12`); model over-assigning `reported` on vague text; checklist items too coarse; users reading the output as a grade.

**Deferred.** Overall scores, code-repository analysis, supplementary-material handling, automatic environment reconstruction.

---

## Cross-phase gate: Reliability and release readiness (M14)

**Objective.** Confirm that the whole MVP-1 meets the PRD's non-functional requirements and that claims about it are backed by records.

**Why needed.** Individual phases check their own features; this gate checks the whole.

**Prerequisites.** Phases 7–11 completed or explicitly descoped in `progress.md` with reasons.

**Tasks.**

| Task | Description | Requirements |
|---|---|---|
| M14-T1 | Clean-environment test: fresh clone, README instructions only, migrations on an empty database, full test run. | NFR-MNT-002, NFR-TST-001 |
| M14-T2 | Security review against `NFR-SEC-001..006` and `CLAUDE.md` security rules; secret scan of the whole history; confirm GROBID and database are not exposed; confirm no internals in error responses. | NFR-SEC-* |
| M14-T3 | Privacy review: what paper text leaves the machine, and to whom; README statement; log inspection. | NFR-PRI-001, NFR-PRI-002 |
| M14-T4 | Re-run all evaluations; compare to earlier baselines; record regressions. | NFR-COR-002 |
| M14-T5 | Accessibility and interface-quality check of key screens (keyboard use, labels, non-colour status, reduced motion, browser inspection at representative viewports). | NFR-ACC-001, NFR-UX-001 |
| M14-T6 | Known-limitations document and an honest README. Confirm every statement in the README about capability is backed by an evidence entry. | NFR-COR-001 |
| M14-T7 | Dependency and licence review of what was added during the project. | — |

**Acceptance criteria.** All tasks above have evidence in `progress.md`; every open `OQ-xxx` is resolved, deferred with a reason, or accepted as a known limitation.

**Definition of done.** Developer sign-off recorded; MVP-1 declared in `progress.md`.

**Risks and failure cases.** Findings that require rework in earlier phases (record and schedule them; do not hide them); documentation drift.

**Deferred.** Production deployment, performance tuning beyond baselines.

---

## Phase 12: Future extensions (not scheduled)

Nothing here is started without the evidence or constraint listed. Each start is a new, recorded decision.

| Extension | What would justify starting it |
|---|---|
| Human correction records and review workflow | Users or evaluation show that extraction or checklist errors need manual correction to be useful; statuses `human_confirmed` and `human_rejected` are already reserved. |
| Knowledge graph | A concrete query that the relational model cannot answer reasonably (for example repeated multi-hop questions across papers), plus a stable entity-normalisation method. |
| Research-gap exploration | Reliable cross-paper comparison data exists, and outputs can be framed as hypotheses linked to evidence (`PRD §3.2`). |
| Code repository analysis (static) | A requirement to relate papers to released code, a safe static-analysis design, and a decision that never executes repository code. |
| Asynchronous jobs / workers | Measured parse or extraction time makes request-bound processing unacceptable, or concurrency conflicts appear (`AD-010`). |
| Object storage | Deployment beyond one machine, or files too large/numerous for local disk (`AD-002`). |
| Authentication and multi-user support | Any shared or networked deployment, or a second user needing separate data (`AD-009`, `NFR-SEC-006`). |
| Deployment | A target environment and security posture decided, after authentication. |
| Advanced evaluation (larger sets, automated judge, CI evaluation) | Recorded evidence that the small evaluation set cannot discriminate between changes, and a judge validated against human labels. |
| Re-parse / parser upgrade workflow | A parser change that produces better passages, and a policy that keeps evidence links valid (`OQ-006`). |
| OCR for scanned papers | Users repeatedly need scanned papers, and detection plus failure status (`FR-ING-003`) is in place. |
| Tracing/observability tooling | Debugging LLM pipelines from structured logs becomes the bottleneck (`AD-016`). |

---

## Appendix: Roadmap change control

- A change of scope, order or exit criteria is made here **and**, if it alters requirements, in `PRD.md`; `progress.md` records the date and reason.
- If an experiment (Phase 1, 4, 8) contradicts an assumption, update the affected decision (`AD-xxx`) and open question; do not carry on silently.
- Do not shorten a phase by dropping tests or evidence recording; reduce scope instead.
