# Design note: core schema (P2-T1)

| Field | Value |
|---|---|
| Status | Implemented 2026-11-03 by migration `d2ea199dd3d3` (P2-T3); models in `backend/app/models/`. Constraint tests follow in P2-T5. |
| Tables | `papers`, `documents`, `passages` only (Phase 2 definition of done) |
| Requirements | `DR-001`..`DR-009`, `FR-ING-001`..`FR-ING-010`, PRD §8.2 and §8.3, `NFR-MNT-002` |
| Inputs | `docs/design/parser-output.md` (fields, regions, failure reasons) |
| Database | PostgreSQL 18.6 (`pgvector/pgvector:0.8.7-pg18-trixie`); pgvector not enabled |

## 1. Relationships

```
papers 1 ──< documents 1 ──< passages
          (paper_id, nullable       (document_id, required)
           until parsed)
```

- **A paper may have several documents** (PRD §8.3: a preprint and a publisher version with the same DOI). One document belongs to at most one paper.
- A document exists from upload (`pending`) but its paper is only known after parsing, because the DOI comes from the parse. So `documents.paper_id` is nullable, and required once a document is `parsed`.
- Passages belong to exactly one document. Answers are not stored (PRD §8.2).

## 2. Conventions

| Topic | Choice | Reason |
|---|---|---|
| Primary keys | `uuid`, default `uuidv7()` | `DR-003`. UUIDv7 is time-ordered, which keeps index inserts local; built into PostgreSQL 18 (checked live 2026-11-03) |
| Enumerations | `text` + `CHECK (... IN (...))` | Adding a value later is a one-line migration; PostgreSQL `ENUM` types are harder to change with Alembic |
| Unknown values | `NULL`, never `''` or `0` | `DR-006`, `DR-007`. `CHECK` constraints reject empty strings and page 0 |
| Timestamps | `timestamptz NOT NULL DEFAULT now()` | |
| Deletes | Foreign keys `ON DELETE RESTRICT` | `DR-008`: nothing is removed by cascade; deleting documents is not a VS-1 feature |
| Names | Plural snake_case tables; constraints named explicitly (`ck_`, `uq_`, `fk_`, `ix_` prefixes) | Readable migration errors and tests |

## 3. `papers`

A scholarly work at metadata level (PRD §1.6).

| Column | Type | Null | Constraint / note |
|---|---|---|---|
| `id` | `uuid` | no | PK, default `uuidv7()` |
| `title` | `text` | yes | `CHECK (title <> '')` |
| `authors` | `text[]` | no | default `'{}'`; empty array when none are found |
| `abstract` | `text` | yes | `CHECK (abstract <> '')`. Metadata copy; the abstract is also stored as `abstract` passages for citation |
| `doi` | `text` | yes | As found in the document, for display |
| `doi_normalized` | `text` | yes | **Unique** (`uq_papers_doi_normalized`); several papers without a DOI are allowed (checked live: `UNIQUE` permits many `NULL`s). `CHECK (doi_normalized LIKE '10.%')`. Produced by `normalize_doi` in `backend/app/services/doi.py` (P2-T4): trimmed, resolver prefix or `doi:` removed, lower-cased. A value that is not a DOI gives `NULL` for both `doi` and `doi_normalized` |
| `metadata_source` | `text` | no | `CHECK (metadata_source IN ('grobid'))` (`FR-ING-006`) |
| `created_at` | `timestamptz` | no | default `now()` |

`CHECK ((doi IS NULL) = (doi_normalized IS NULL))`.

Metadata is written once, from the first parsed document of the paper. A later document with the same DOI is attached without overwriting the paper's metadata (`DR-008`).

## 4. `documents`

One uploaded file, identified by its content hash.

| Column | Type | Null | Constraint / note |
|---|---|---|---|
| `id` | `uuid` | no | PK, default `uuidv7()` |
| `paper_id` | `uuid` | yes | FK → `papers.id`, `ON DELETE RESTRICT` |
| `sha256` | `text` | no | **Unique** (`uq_documents_sha256`); `CHECK (sha256 ~ '^[0-9a-f]{64}$')` |
| `size_bytes` | `bigint` | no | `CHECK (size_bytes > 0)` |
| `storage_key` | `text` | no | **Unique**; generated key, never the client filename (`NFR-SEC-002`) |
| `original_filename` | `text` | yes | Display only, never used as a path; `CHECK (char_length(original_filename) BETWEEN 1 AND 255)` |
| `status` | `text` | no | default `'pending'`; `CHECK (status IN ('pending','processing','parsed','failed'))` |
| `failure_reason` | `text` | yes | `CHECK` against the list in §6 |
| `failure_message` | `text` | yes | Short, no paper text, no stack trace; `CHECK (char_length(failure_message) <= 1000)` |
| `parser_name` | `text` | yes | `'grobid'` (`DR-005`) |
| `parser_version` | `text` | yes | For example `'0.9.1'` |
| `parser_config` | `jsonb` | yes | The fixed GROBID request fields (`docs/design/parser-output.md` §2) |
| `tei_storage_key` | `text` | yes | **Unique**; raw TEI artifact (`FR-ING-005`) |
| `page_count` | `integer` | yes | `CHECK (page_count > 0)` |
| `skipped_paragraphs` | `integer` | yes | `CHECK (>= 0)` |
| `joined_paragraphs` | `integer` | yes | `CHECK (>= 0)` |
| `processing_started_at` | `timestamptz` | yes | Set when status becomes `processing`; used by `FR-ING-010` recovery |
| `created_at` | `timestamptz` | no | default `now()` |
| `updated_at` | `timestamptz` | no | default `now()`; set on every status change |

**Status rules (table `CHECK` constraints):**

| Rule | Constraint |
|---|---|
| A failure reason exactly when failed | `(status = 'failed') = (failure_reason IS NOT NULL)` |
| A message only when failed | `failure_message IS NULL OR status = 'failed'` |
| A parsed document has a paper, a parser record and its TEI artifact | `status <> 'parsed' OR (paper_id IS NOT NULL AND parser_name IS NOT NULL AND parser_version IS NOT NULL AND tei_storage_key IS NOT NULL)` |
| Processing has a start time | `status <> 'processing' OR processing_started_at IS NOT NULL` |

**Rules kept in code and covered by tests** (not expressible as a simple `CHECK`): a `parsed` document has at least one `body` passage; a `failed` document has no passages; passages are written in the same transaction that sets `parsed` (`FR-ING-002`, PRD §8.3).

## 5. `passages`

Immutable source text (`DR-002`, `DR-004`), one row per passage from `docs/design/parser-output.md`.

| Column | Type | Null | Constraint / note |
|---|---|---|---|
| `id` | `uuid` | no | PK, default `uuidv7()`; the identity used by citations and evidence |
| `document_id` | `uuid` | no | FK → `documents.id`, `ON DELETE RESTRICT` |
| `ordinal` | `integer` | no | `CHECK (ordinal >= 0)`; **unique per document** (`uq_passages_document_id_ordinal`) |
| `region` | `text` | no | `CHECK (region IN ('abstract','body','caption','back'))` |
| `back_type` | `text` | yes | `CHECK (back_type IS NULL OR region = 'back')`; GROBID's type, stored as given |
| `section_number` | `text` | yes | `CHECK (section_number <> '')` |
| `section_title` | `text` | yes | `CHECK (section_title <> '')` |
| `section_path` | `text` | yes | **Generated, stored:** `section_number || ' ' || section_title`, or `section_title` when there is no number (checked live). Satisfies PRD §8.2 without storing the same fact twice |
| `text` | `text` | no | `CHECK (text <> '')`; whitespace-collapsed TEI text, never edited |
| `page_start` | `integer` | yes | `CHECK (page_start IS NULL OR page_start >= 1)` |
| `page_end` | `integer` | yes | `CHECK ((page_start IS NULL) = (page_end IS NULL))`, `CHECK (page_end >= page_start)` |
| `created_at` | `timestamptz` | no | default `now()` |

**Immutability at database level:** a `BEFORE UPDATE` trigger on `passages` raises "passages are immutable" (checked live). This makes `DR-004` impossible to break by accident. Phase 2 acceptance criterion 4 leaves this optional; it is chosen because it costs one small function. Inserts are still allowed; deletes are blocked for documents by `ON DELETE RESTRICT` and are not part of any VS-1 flow.

No full-text column yet: it arrives with keyword retrieval in Phase 4 (`FR-RET-001`).

## 6. Failure reasons

**Stored on `documents` (`failure_reason`):** these documents exist, keep their file, have no passages, and may be retried (PRD §8.3).

| Value | Meaning (from `docs/design/parser-output.md` §7) |
|---|---|
| `parser_unreachable` | GROBID refused the connection |
| `parser_disconnected` | GROBID dropped the connection mid-request |
| `parser_timeout` | No response in time, or GROBID `TIMEOUT` |
| `parser_busy` | GROBID still returned 503 after the retries |
| `unreadable_pdf` | GROBID `BAD_INPUT_DATA` (for example a truncated PDF) |
| `no_text_layer` | GROBID `NO_BLOCKS` (likely scanned or image-only) |
| `document_too_long` | GROBID `TOO_MANY_TOKENS` or `TOO_MANY_BLOCKS` |
| `parser_error` | Any other GROBID error, or 400 |
| `malformed_tei` | The returned TEI is not well-formed XML |
| `empty_parse` | No body passage after parsing, or GROBID 204 |
| `storage_error` | The TEI artifact could not be stored |
| `interrupted` | Left `processing` when the server stopped (`FR-ING-010`) |

**Not stored (upload rejected, no document row):** `not_pdf`, `empty_file`, `file_too_large`. These are returned as structured API errors by the upload endpoint (`FR-ING-001`, `NFR-SEC-005`). A failure to store the uploaded file itself also creates no row (`FR-ING-002`).

## 7. Indexes

| Index | Purpose |
|---|---|
| Unique: `documents.sha256`, `documents.storage_key`, `documents.tei_storage_key`, `papers.doi_normalized`, `passages (document_id, ordinal)` | Constraints above; also serve look-ups by hash, DOI and passage order |
| `ix_documents_paper_id` on `documents (paper_id)` | Documents of a paper |
| `ix_documents_processing` on `documents (processing_started_at) WHERE status = 'processing'` | Startup recovery scan (`FR-ING-010`) |

Nothing else until a query needs it.

## 8. How PRD §8.3 maps to the schema

| Situation | Mechanism |
|---|---|
| Identical file uploaded again | Unique `sha256`: the insert conflicts and the existing document is returned (also safe for concurrent uploads) |
| Different file, same DOI | New document row; at parse time its `paper_id` is set to the existing paper found by `doi_normalized` |
| No DOI | New paper with `doi` and `doi_normalized` both `NULL`; unique index allows many |
| Parser failure | `status = 'failed'`, `failure_reason` set, no passages; the file and its row are kept |
| Retry of a failed document | `failed` → `processing` → `parsed`/`failed` on the same row; previous reason cleared by the status rule |
| Process crash | Rows still `processing` found through `ix_documents_processing` and set `failed` / `interrupted` |
| Re-parse of a parsed document | Not supported in VS-1 (`OQ-006`); the immutability trigger prevents in-place edits |

## 9. Tests this design requires (P2-T5)

Migration applies to an empty database; duplicate `sha256` rejected; two documents under one paper allowed; duplicate `doi_normalized` rejected while several `NULL` DOIs are accepted; foreign-key violation rejected; invalid `status`, `region` and `failure_reason` rejected; `failed` without reason and reason without `failed` rejected; `parsed` without paper or TEI key rejected; duplicate passage ordinal rejected; page 0 and `page_end < page_start` rejected; null page stored and read back as `NULL`; empty strings rejected; passage update rejected by the trigger; `section_path` generated correctly.
