# GROBID feasibility experiment (Phase 1, M3)

| Field | Value |
|---|---|
| Status | **In progress.** P1-T1 (documentation) done 2026-11-03. P1-T2 to P1-T8 not started. |
| Answers | `OQ-001`, `OQ-002`, `OQ-003`, `OQ-005`, `OQ-013`, `OQ-016` (in P1-T6) |
| Rule | Nothing here is a claim about real papers until it has been observed. Where documentation and observation differ, observation wins and the difference is recorded. |

## 1. Setup

| Item | Value | How known |
|---|---|---|
| GROBID | 0.9.1, image `grobid/grobid:0.9.1-crf` (CRF/Wapiti models only, CPU) | `/api/version`; `compose.yaml` |
| Models loaded | 12 CRF models, 0 failed | `/api/health`, 2026-11-03 |
| Service address | `http://127.0.0.1:8070`, published on 127.0.0.1 only | `compose.yaml`; checked in P0-T3 |
| Licence | Apache-2.0 (documentation CC-0, training data CC-BY) | GROBID README |

## 2. P1-T1: documentation read (2026-11-03)

Pages read: [Grobid-service](https://grobid.readthedocs.io/en/latest/Grobid-service/), [Consolidation](https://grobid.readthedocs.io/en/latest/Consolidation/), [Coordinates-in-PDF](https://grobid.readthedocs.io/en/latest/Coordinates-in-PDF/), [Configuration](https://grobid.readthedocs.io/en/latest/Configuration/), [Grobid-docker](https://grobid.readthedocs.io/en/latest/Grobid-docker/), [TEI-encoding-of-results](https://grobid.readthedocs.io/en/latest/TEI-encoding-of-results/), [Grobid-specialized-processes](https://grobid.readthedocs.io/en/latest/Grobid-specialized-processes/).

"Checked" means verified against the running service on 2026-11-03; "doc only" means not yet observed.

### 2.1 Full-text endpoint

`POST` (or `PUT`) `/api/processFulltextDocument`, `multipart/form-data`, returns `application/xml` (TEI).

| Parameter | Values (default **bold**) | Note for PaperPilot |
|---|---|---|
| `input` | PDF file (required) | Missing `input` returns **400**: checked |
| `consolidateHeader` | 0 none, **1** consolidate and inject metadata, 2 DOI only, 3 using extracted DOI only | **Default calls CrossRef** (see §2.3). Use `0` |
| `consolidateCitations` | **0**, 1, 2 | Keep `0` |
| `consolidateFunders` | **0**, 1, 2 | Keep `0` |
| `includeRawCitations`, `includeRawAffiliations`, `includeRawCopyrights` | **0**, 1 | Raw citations may help `OQ-003`; try in P1-T4 |
| `teiCoordinates` | element names, one form field each: `p`, `head`, `s`, `figure` (figures and tables), `biblStruct`, `persName`, `ref`, `formula`, `note`, `title`, `affiliation` | Needed for page numbers (§2.4) |
| `segmentSentences` | flag, `1` to enable | Splits paragraphs into `<s>` sentences. Not needed for passages (`AD-004`); possibly useful for quote matching (`OQ-013`) |
| `generateIDs` | `1` to enable | Stable element IDs inside one parse; try in P1-T4 |
| `start`, `end` | 1-based pages, **-1** = first/last | Not needed |
| `flavor` | none, `article/light`, `article/light-ref`, `sdo/ietf` | Not used: `article/light` collapses the body into one paragraph |

Other documented endpoints: `/api/isalive` (checked), `/api/health` (checked), `/api/version` (checked), `/api/processHeaderDocument`, `/api/processReferences`, and others not needed now. A `GET` on the full-text endpoint returns **405**: checked.

### 2.2 Responses and errors

| HTTP | Documented meaning | PaperPilot mapping (proposed for `FR-ING-003`, decided in P3-T3) |
|---|---|---|
| 200 | TEI produced | Inspect content; an empty body is still a failure (`empty_parse`) |
| 204 | "no content could be extracted and structured" | `failed` |
| 400 | wrong request or missing parameter | Our bug: `failed`, logged |
| 500 | internal error, with a code in the message: `BAD_INPUT_DATA`, `NO_BLOCKS`, `TOO_MANY_BLOCKS`, `TOO_MANY_TOKENS`, `TIMEOUT`, `TAGGING_ERROR`, `PARSING_ERROR`, `GENERAL`, `PDFALTO_CONVERSION_FAILURE` | `failed`, reason from the code |
| 503 | all threads busy | Retry after 5–10 s (documented advice), then `failed` |

Only 400 and 405 have been observed so far. Which inputs produce which code is tested in P1-T5.

### 2.3 Consolidation sends data outside the machine

- The docs: GROBID supports CrossRef (default) and biblio-glutton for consolidation, using "the reliable subset of extracted metadata". The exact fields sent are not documented.
- **Observed:** the image's `grobid.yaml` sets `service: "crossref"` with no `mailto`, and the container can reach `https://api.crossref.org` (HTTP response received).
- `consolidateHeader` defaults to `1`, so **every full-text request would send extracted paper metadata to CrossRef unless the client passes `consolidateHeader=0`**. The PRD does not consider this data flow (`NFR-PRI-001` covers only the LLM provider).
- **Rule for this experiment and for the ingestion client (P3-T3):** always send `consolidateHeader=0`; leave `consolidateCitations` and `consolidateFunders` at `0`. Enabling consolidation would be a separate, recorded decision with a privacy note in `README.md`.

### 2.4 Coordinates and page numbers (`OQ-001`)

- The docs: "Page numbers are not directly in TEI elements." They are recovered from `coords` attributes requested with `teiCoordinates`.
- `coords` format: boxes separated by `;`, each `page,x,y,width,height`, page starting at 1, PDF units, origin top-left. Page sizes appear in `<facsimile><surface n=".." ...>`.
- `<pb>` page-break elements: not mentioned in the docs. **Unknown until observed.**
- Plan for P1-T3: request `teiCoordinates` for `p`, `head`, `figure` and `biblStruct` and check whether every paragraph gets a page (and whether a paragraph can span pages, giving two boxes on different pages).

### 2.5 TEI structure

The TEI documentation page describes only the schema (`grobid-home/schemas/`), not where each element appears. Where title, authors, abstract, DOI, sections, paragraphs, references, figures and tables appear in the output is **unknown until observed** in P1-T4 and recorded there.

### 2.6 Limits and configuration

| Setting | Docs | Observed in the image's `grobid.yaml` |
|---|---|---|
| `concurrency` | 10 (example) | 10 |
| `poolMaxWait` | 1 s | 1 |
| pdfalto `timeoutSec` | 60 | **120** |
| pdfalto `memoryLimitMb` | 6096 | 6096 |
| `blocksMax` | 100000 | **200000** |
| `tokensMax` | 1000000 | 1000000 |
| `modelPreload` | true | true |
| `corsAllowedOrigins` | `*` | `*` (acceptable only because the port is bound to 127.0.0.1) |

- No HTTP request timeout is documented for the service itself; PaperPilot's own client timeout (`GROBID_TIMEOUT_SECONDS`, placeholder 120 s) must cover it. Real parse times are measured in P1-T3.
- No page-count or file-size limit is documented beyond the block, token, memory and timeout limits. The upload limit (`OQ-005`) comes from measuring real papers.
- Memory: docs recommend 4 GB for full-text processing; the container used about 3.2 GB at idle (P0-T3).

## 3. Still to do

| Task | What |
|---|---|
| P1-T2 | Choose 3–5 papers the developer is permitted to use, with varied layouts. Record title, source and licence. PDFs stay out of git (`data/` is ignored). |
| P1-T3 | Script under `scripts/` sends each paper with `consolidateHeader=0` and the coordinates above; saves raw TEI under `data/`; records status and time. |
| P1-T4 | Inspect each TEI against the checklist in the roadmap; fill §2.4 and §2.5 with observations. |
| P1-T5 | Failure inputs; record actual codes against §2.2. |
| P1-T6 | Answers or deferrals for the open questions. |
| P1-T7 | Parser-output representation (design note). |
| P1-T8 | Go / go-with-limits / no-go. |
