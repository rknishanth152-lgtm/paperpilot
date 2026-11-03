# GROBID feasibility experiment (Phase 1, M3)

| Field | Value |
|---|---|
| Status | **In progress.** P1-T1 (documentation), P1-T2 (papers), P1-T3 (GROBID runs), P1-T4 (inspection) and P1-T5 (failure inputs) done 2026-11-03. P1-T6 to P1-T8 not started. |
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

**Observed in P1-T5 (§6):** 400, 405, 500 with `BAD_INPUT_DATA`, `NO_BLOCKS` and `TOO_MANY_TOKENS`, 503 under load, and **200 with an empty body**. 204 was not observed.

### 2.3 Consolidation sends data outside the machine

- The docs: GROBID supports CrossRef (default) and biblio-glutton for consolidation, using "the reliable subset of extracted metadata". The exact fields sent are not documented.
- **Observed:** the image's `grobid.yaml` sets `service: "crossref"` with no `mailto`, and the container can reach `https://api.crossref.org` (HTTP response received).
- `consolidateHeader` defaults to `1`, so **every full-text request would send extracted paper metadata to CrossRef unless the client passes `consolidateHeader=0`**. The PRD does not consider this data flow (`NFR-PRI-001` covers only the LLM provider).
- **Rule for this experiment and for the ingestion client (P3-T3):** always send `consolidateHeader=0`; leave `consolidateCitations` and `consolidateFunders` at `0`. Enabling consolidation would be a separate, recorded decision with a privacy note in `README.md`.

### 2.4 Coordinates and page numbers (`OQ-001`)

- The docs: "Page numbers are not directly in TEI elements." They are recovered from `coords` attributes requested with `teiCoordinates`.
- `coords` format: boxes separated by `;`, each `page,x,y,width,height`, page starting at 1, PDF units, origin top-left. Page sizes appear in `<facsimile><surface n=".." ...>`.
- `<pb>` page-break elements: not mentioned in the docs. **Observed (P1-T4): none in any of the five outputs.**
- Plan for P1-T3: request `teiCoordinates` for `p`, `head`, `figure` and `biblStruct` and check whether every paragraph gets a page (and whether a paragraph can span pages, giving two boxes on different pages).

### 2.5 TEI structure

The TEI documentation page describes only the schema (`grobid-home/schemas/`), not where each element appears. **Observed in P1-T4: see §5.1.**

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

## 4. P1-T3: sending the papers to GROBID (2026-11-03)

Script: `scripts/grobid_experiment.py` (throwaway). Run from the repository root with the services up:

```bash
$env:PYTHONPATH = "backend"; uv run python scripts/grobid_experiment.py
```

It posts each PDF in `data/papers/` to `/api/processFulltextDocument` one at a time with a 300 s client timeout, saves `data/grobid-output/<paper>.tei.xml` and a JSON run record (`run-<UTC time>.json`: GROBID version, form fields, per-file SHA-256, status, seconds, TEI size, page count). It prints no paper text. Outputs are git-ignored.

Form fields used for every paper: `consolidateHeader=0`, `consolidateCitations=0`, `consolidateFunders=0`, `includeRawCitations=1`, `generateIDs=1`, `teiCoordinates` = `p`, `head`, `figure`, `biblStruct`.

### 4.1 Results

| Paper | HTTP | Seconds, run 1 | Seconds, run 2 | Pages (`<facsimile>`) | TEI bytes |
|---|---|---|---|---|---|
| p1 BERT | 200 | 11.04 | 2.37 | 16 | 187,303 |
| p2 eLife | 200 | 5.47 | 2.93 | 30 | 302,588 |
| p3 PLOS Med | 200 | 1.82 | 1.60 | 6 | 105,576 |
| p4 PLOS ONE 2007 | 200 | 1.72 | 1.61 | 5 | 88,113 |
| p5 PLOS ONE 2011 | 200 | 1.43 | 1.38 | 4 | 58,527 |

GROBID 0.9.1, CRF image, CPU only, sequential requests, on the developer's laptop (AMD Ryzen AI 9 365, 20 threads available to Docker). Container memory rose from about 3.2 GB at idle to about 3.95 GB after the run.

### 4.2 Observations

- **All five papers parsed** (HTTP 200); page counts match the PDFs.
- **First request is slower.** p1 took 11.0 s on the first run and 2.4 s on the second; the first request after start-up includes warm-up. Steady-state times were 1.4–2.9 s for 4–30 pages. The 120 s placeholder `GROBID_TIMEOUT_SECONDS` is far above anything observed; it stays a placeholder until larger papers are tried (`NFR-PRF-001`).
- **Output is repeatable except for IDs and a timestamp.** Two runs produced different bytes (68–211 changed lines per file), but after removing `xml:id`/`ref` values of the form `_XXXXXXX` and the `when` timestamp, all five outputs were identical, body included. `generateIDs=1` creates **random IDs on every run**, so they must never be used as stable identifiers for passages or evidence (passage IDs come from PaperPilot's own database, `DR-003`).
- **No consolidation happened.** The TEI contains no `status="consolidated"` or `source="crossref"`/`"glutton"` markers, and the GROBID container log has no line mentioning CrossRef or consolidation.

## 5. P1-T4: inspection of the output (2026-11-03)

Tools (throwaway, in `scripts/`): `inspect_tei.py` counts checklist items per paper; `quote_match.py` checks whether GROBID sentences occur in the PDF text layer, extracted with `pdfalto` 0.6.2 inside the GROBID container (`-skipGraphs -readingOrder`). Results are saved in git-ignored `data/`. Paragraph text was looked at only as short snippets.

### 5.1 Where things are in the TEI (observed)

| Item | Location |
|---|---|
| Title | `teiHeader/fileDesc/titleStmt/title` |
| Authors | `teiHeader/fileDesc/sourceDesc/biblStruct/analytic/author/persName` |
| Abstract | `teiHeader/profileDesc/abstract//p` |
| DOI | `teiHeader/fileDesc/sourceDesc/biblStruct/idno[@type='DOI']` |
| Sections | `text/body/div`, each with one `head` and its `p` elements; **always flat** (no nested `div` in any paper) |
| Section numbers | `head/@n` when the paper numbers its headings (BERT only) |
| Footnotes, running headers and footers | `text/body/note` (separate from paragraphs) |
| Figures and tables | `text/body/figure`; tables have `@type='table'` and `table/row` |
| References | `text/back//listBibl/biblStruct`, with the raw string in `note[@type='raw_reference']` |
| Acknowledgements, funding, appendices | `text/back/div` |
| Pages | `facsimile/surface` (one per page); per element in `@coords`, as line-level boxes `page,x,y,w,h;…`. No `<pb>` elements |

### 5.2 Checklist results

| Check | p1 BERT | p2 eLife | p3 PLOS Med | p4 PLOS ONE 2007 | p5 PLOS ONE 2011 |
|---|---|---|---|---|---|
| Title / authors / abstract | yes / 4 / yes | yes / 7 / yes | yes / 1 / yes | yes / 3 / yes | yes / 4 / yes |
| DOI in TEI | no (not checked whether printed in the PDF) | yes | yes | yes | yes |
| Body sections (headings numbered) | 28 (18) | 30 (0) | 10 (0) | 8 (0) | 4 (0) |
| Body paragraphs; median length (chars) | 99; 315 | 77; 801 | 25; 1,024 | 29; 447 | 12; 966 |
| Paragraphs with a page from `coords` | **99/99** | **77/77** | **25/25** | **29/29** | **12/12** |
| Paragraphs spanning two pages | 8 | 14 | 3 | 1 | 2 |
| Paragraphs starting lowercase (split mid-sentence) | 3 | 3 | 2 | 0 | 0 |
| Running header/footer text inside paragraphs (pattern search) | none found | none found | none found | none found | none found |
| Header/footer text captured as body `note` | — | yes ("Errington et al. eLife 2021;…") | — | yes ("PLoS ONE \| www.plosone.org", issue line) | yes (same) |
| Tables found / with rows | 3 / 3 | 6 / 6 | 4 / 4 | 2 / 2 | 0 / 0 |
| References (all with raw string and page) | 55 | 84 | 37 | 37 | 26 |

### 5.3 Problems found

1. **Paragraphs split at column or page breaks.** Up to three per paper start mid-sentence with a lowercase word, continuing the previous paragraph (for example a paragraph ending "…Additional" followed by one starting "ablation studies can be found in Appendix C."). One logical paragraph becomes two passages with broken sentences (`OQ-002`, `RISK-03`).
2. **Footnotes leak into body text in BERT.** A footnote became its own paragraph ("10 https://gluebenchmark.com/leaderboard"), footnote markers remain as stray numbers ("…by a wide margin. 12"), and two paragraphs contain only "...".
3. **Sidebar and pull-quote text becomes sections** in PLOS Medicine: the journal's box "The Essay section contains opinion pieces…" and a pull quote appear as section headings with their own paragraphs.
4. **Figure/table errors.** PLOS ONE 2007: Table 2 typed as a figure (the paper has 3 tables; 2 found). eLife: Figure 5 not among the figures; one reference ("Wilson DJ. 2019…") captured as a body note. BERT: Table 3 not identified as a table; the appendix (including Tables 5–8) is placed in `back`, not `body`. PLOS ONE 2011: one figure entry with no label. PLOS Medicine: the one `formula` element contains table-cell text. eLife: the funding table's cells appear as headings in `back`.
5. **Citation markers are rewritten.** GROBID changes in-text citations: "[9–11]" in the PDF becomes "[9][10][11]", and "(Peters et al., 2017, 2018a)" becomes "(Peters et al., 2017(Peters et al., , 2018a) )". Passage text is therefore **not** verbatim PDF text around citations.
6. **Broken ligatures come from the PDF itself.** PLOS Medicine's text layer contains "fi ndings", "confi rmation", "defi ned" (125 such splits in the body), and GROBID copies them. They occur mid-word as well as at word starts.
7. **`generateIDs` IDs are random per run** (P1-T3); only usable inside one parse.

### 5.4 Matching GROBID text to the PDF text layer (`OQ-013`)

Sentences of at least 40 characters from body paragraphs, searched in the pdfalto text after normalising both sides:

| Paper | Sentences | Whitespace only | + NFKC, ligature characters, line-end hyphenation, "fi x" splits at word start | Upper bound: no spaces or hyphens, lower-case |
|---|---|---|---|---|
| p1 BERT | 261 | 28% | 82% | 87% |
| p2 eLife | 398 | 53% | 63% | 88% |
| p3 PLOS Med | 167 | 24% | 77% | 78% |
| p4 PLOS ONE 2007 | 107 | 65% | 68% | 93% |
| p5 PLOS ONE 2011 | 65 | 85% | 86% | 91% |

Of the sentences missed even at the upper bound (34, 48, 36, 8, 6), between 2 and 16 per paper are **interrupted** in the PDF text (both halves found, separated by other text); the rest **differ**, mainly because of rewritten citation markers (item 5), mid-word ligature splits (item 6) and different text order between pdfalto and GROBID.

**What this means (input to P1-T6):** quotes cannot be verified reliably against the PDF text layer. They must be verified against the stored passage text, which is what `FR-CIT-002` already specifies, with normalisation for at least whitespace, Unicode compatibility forms, ligature characters, line-end hyphenation and space-split ligatures. Highlighting a quote inside the original PDF would need separate, fuzzy matching and is not part of VS-1.

## 6. P1-T5: failure inputs (2026-11-03)

Script: `scripts/grobid_failures.py` (throwaway). `inputs` mode generates test files in git-ignored `data/failure-inputs/` with the standard library (synthetic text, no real paper content, except truncated copies of p1 and p2) and posts each with all consolidation off. `service` mode stops and restarts GROBID with Docker Compose. Results: `data/grobid-output/failures-*.json`.

### 6.1 Bad and extreme inputs

| Input | Bytes | Result | GROBID message | Seconds |
|---|---|---|---|---|
| Text file renamed `.pdf` | 760 | 500 | `[BAD_INPUT_DATA] PDF to XML conversion failed with error code: 1` | 0.06 |
| Empty file | 0 | 500 | same `BAD_INPUT_DATA` | 1.01 |
| `%PDF-1.4` header then random bytes | 50,009 | 500 | same `BAD_INPUT_DATA` | 1.02 |
| p1 truncated to 50% | 393,139 | 500 | same `BAD_INPUT_DATA` | 1.03 |
| p2 truncated to 10% | 184,690 | 500 | same `BAD_INPUT_DATA` | 1.03 |
| Synthetic 1-page text PDF (control) | 3,455 | **200, body empty** | text placed in one `back` paragraph | 1.08 |
| Image-only page, no text layer (stand-in for a scanned PDF) | 21,743 | 500 | `[NO_BLOCKS] PDF parsing resulted in empty content` | 1.02 |
| Blank page | 549 | 500 | same `NO_BLOCKS` | 1.02 |
| Synthetic 300-page text PDF | 960,013 | **200, body empty** | as the 1-page control | 10.29 |
| Synthetic 3,000-page text PDF | 9,727,865 | 500 | `[TOO_MANY_TOKENS] The document has 2883000 tokens, but the limit is 1000000` | 16.86 |
| One-page PDF with a 64 MB noise image | 67,500,318 | 500 | `NO_BLOCKS` | 1.86 |

### 6.2 Service failures

| Case | Result | Seconds |
|---|---|---|
| GROBID stopped before the request | `httpx.ConnectError` (connection refused) | 2.05 |
| GROBID stopped 5 s into a request (3,000-page input) | `httpx.RemoteProtocolError`: "Server disconnected without sending a response." | 8.53 |
| Time from `docker compose start grobid` until `/api/isalive` is `true` | 24.4 and 22.7 (two restarts) | — |
| 25 concurrent requests (p2, `concurrency: 10`) | **10 × 200, 15 × 503**; the 503 body is an HTML error page, not JSON | 1.5–27.5 |

### 6.3 Observations

1. **A 200 response does not mean the paper was parsed.** GROBID returned 200 with an empty body for synthetic text that does not look like an article. Ingestion must check for body paragraphs and set `failed` with `empty_parse` when there are none (`FR-ING-003`).
2. **Non-PDF, empty, corrupt and truncated files all give the same `BAD_INPUT_DATA` code.** GROBID does not distinguish them, so PaperPilot's own upload validation (PDF signature, empty file, size; `FR-ING-001`) must catch what it can **before** calling GROBID, with its own reason codes. A truncated file with a valid header passes a signature check and is reported by GROBID.
3. **No-text PDFs are detectable:** image-only and blank pages give `NO_BLOCKS`. A real scanned paper was not tested (no licensed example), so mapping `NO_BLOCKS` to a "likely scanned" reason is a reasonable inference, not an observation.
4. **Long documents fail with a clear code** (`TOO_MANY_TOKENS`) rather than timing out; 300 synthetic pages took about 10 s and 3,000 pages about 17 s.
5. **GROBID has no file-size limit of its own:** a 64 MB file was accepted and processed in under 2 s. The upload limit (`OQ-005`) must be enforced by PaperPilot; the five real papers are 0.09–1.85 MB.
6. **Unreachable and interrupted GROBID give different transport errors** (`ConnectError`, `RemoteProtocolError`); both must map to `failed` with distinct reasons, and an interrupted request leaves nothing to clean up on GROBID's side.
7. **503 under load is real** and arrives as HTML. The client must retry after a pause (documented advice: 5–10 s) and must not try to parse the 503 body.
8. **Restarting GROBID takes about 23–24 s** before it accepts requests; the first request afterwards is slower (P1-T3).
9. **Not observed:** HTTP 204, `TIMEOUT`, `TOO_MANY_BLOCKS`, `PDFALTO_CONVERSION_FAILURE`, encrypted PDFs, and a real scanned paper.

## 7. Still to do

| Task | What |
|---|---|
| P1-T6 | Answers or deferrals for the open questions. |
| P1-T7 | Parser-output representation (design note). |
| P1-T8 | Go / go-with-limits / no-go. |
