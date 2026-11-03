# GROBID feasibility experiment (Phase 1, M3)

| Field | Value |
|---|---|
| Status | **In progress.** P1-T1 (documentation) and P1-T2 (papers) done 2026-11-03. P1-T3 to P1-T8 not started. |
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

## 3. P1-T2: papers (2026-11-03)

Proposed by Claude, approved by the developer. Each licence statement was read on the publisher's page and each PDF was downloaded from the publisher. The PDFs are stored in `data/papers/` (git-ignored) and are **not** committed (`RISK-13`). Page counts are rough estimates from the file; GROBID's `<facsimile>` gives the exact count in P1-T3.

| ID | Paper | Source (PDF) | Licence (where seen) | Chosen to test |
|---|---|---|---|---|
| p1 | Devlin, Chang, Lee, Toutanova. "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding." NAACL 2019. doi:10.18653/v1/N19-1423 | https://aclanthology.org/N19-1423.pdf | CC BY 4.0: ACL Anthology, "Materials published in or after 2016 are licensed on a Creative Commons Attribution 4.0 International License" ([page](https://aclanthology.org/N19-1423/)) | Two-column conference layout, tables, equations, numbered sections |
| p2 | Errington et al. "Investigating the replicability of preclinical cancer biology." eLife 10:e71601, 2021. doi:10.7554/eLife.71601 | https://cdn.elifesciences.org/articles/71601/elife-71601-v3.pdf | CC BY 4.0: "This article is distributed under the terms of the Creative Commons Attribution License" ([page](https://elifesciences.org/articles/71601)) | Long paper, many figures and tables, statistics |
| p3 | Ioannidis. "Why Most Published Research Findings Are False." PLoS Med 2(8): e124, 2005. doi:10.1371/journal.pmed.0020124 | https://journals.plos.org/plosmedicine/article/file?id=10.1371/journal.pmed.0020124&type=printable | CC BY: "open-access article distributed under the terms of the Creative Commons Attribution License" ([page](https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.0020124)) | Essay structure, unusual headings, formulas, tables, older layout |
| p4 | Piwowar, Day, Fridsma. "Sharing Detailed Research Data Is Associated with Increased Citation Rate." PLoS ONE 2(3): e308, 2007. doi:10.1371/journal.pone.0000308 | https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0000308&type=printable | CC BY: "Copyright: © 2007 Piwowar et al. This is an open-access article distributed under the terms of the Creative Commons Attribution License…" ([page](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0000308)) | Short empirical study, 3 tables, 2 figures |
| p5 | Alsheikh-Ali, Qureshi, Al-Mallah, Ioannidis. "Public Availability of Published Research Data in High-Impact Journals." PLoS ONE 6(9): e24357, 2011. doi:10.1371/journal.pone.0024357 | https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0024357&type=printable | CC BY: "Copyright: © 2011 Alsheikh-Ali et al. This is an open-access article distributed under the terms of the Creative Commons Attribution License…" ([page](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0024357)) | Short paper with few tables, later PLOS ONE layout |

| File | Bytes | Rough pages | SHA-256 |
|---|---|---|---|
| `p1-devlin2019-bert.pdf` | 786,279 | ~16 | `987545ffb087f1ece898142c403a516baeabeb70ce19089397fac6f7db12c3d4` |
| `p2-errington2021-elife.pdf` | 1,846,907 | ~30 | `dc1f6a4c3d4824d70855cd7316c75f8d1783349d37b822a9cdb1b665fb609fad` |
| `p3-ioannidis2005-plosmed.pdf` | 255,629 | ~6 | `ffc1005680cb620eec4c913437dfabbf311b535cfe16cbaeb2faec1f92afc362` |
| `p4-piwowar2007-plosone.pdf` | 91,408 | ~5 | `b52ca44dfd09d240543b80315f0cd43fe9ba7946f2b5650d5580213ed5d9186c` |
| `p5-alsheikhali2011-plosone.pdf` | 172,614 | ~4 | `2090a6ed5d95f5f2af6349170c739e80c9362271d66a6f952e315c803290a0cb` |

**Gaps in the sample:** no scanned or weak-text PDF with a verified licence was found, so that case may be impossible in P1-T5 (to be recorded with the reason). Excluded: papers whose pages show only the arXiv non-exclusive licence (for example arXiv 1706.03762) or "© JMLR" (JMLR v15 srivastava14a), because no CC BY statement applies.

To obtain the same files: download each "Source (PDF)" URL into `data/papers/` with the file name above and compare the SHA-256.

## 4. Still to do

| Task | What |
|---|---|
| P1-T3 | Script under `scripts/` sends each paper with `consolidateHeader=0` and the coordinates above; saves raw TEI under `data/`; records status and time. |
| P1-T4 | Inspect each TEI against the checklist in the roadmap; fill §2.4 and §2.5 with observations. |
| P1-T5 | Failure inputs; record actual codes against §2.2. |
| P1-T6 | Answers or deferrals for the open questions. |
| P1-T7 | Parser-output representation (design note). |
| P1-T8 | Go / go-with-limits / no-go. |
