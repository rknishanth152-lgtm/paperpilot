# Design note: parser output representation (P1-T7)

| Field | Value |
|---|---|
| Status | Agreed 2026-11-03 (developer chose the passage regions). Implemented in Phase 3 (P3-T3, P3-T4); not implemented yet. |
| Evidence | `docs/experiments/grobid-feasibility.md` (§ numbers below refer to it) |
| Requirements | `FR-ING-003`..`FR-ING-007`, `DR-001`..`DR-007`, `AD-004`, `OQ-002`, `OQ-003`, `OQ-016` |

This note fixes **what the ingestion module receives from the parser** and **how GROBID's TEI is turned into it**. It is the contract between the GROBID client and the database code. It is not the database schema (P2-T1), but the schema stores these fields.

## 1. Pipeline position

```
PDF bytes ─► validation (P3-T2) ─► GROBID client (P3-T3) ─► raw TEI bytes ─► store artifact (FR-ING-005)
                                                                 │
                                                                 ▼
                                         parse_tei(tei_bytes) -> ParsedDocument     (P3-T4, pure function)
                                                                 │
                                                                 ▼
                                         persist paper, document, passages in one transaction (P3-T5)
```

`parse_tei` is a **pure function** of the stored TEI bytes: same input, same output, no network, no clock, no randomness. Re-running it on a stored artifact reproduces the passages exactly (`FR-ING-005`). GROBID's `generateIDs` IDs are random per run (§4.2), so they are not requested and never used.

## 2. GROBID request (fixed)

| Field | Value | Why |
|---|---|---|
| `consolidateHeader`, `consolidateCitations`, `consolidateFunders` | `0` | The default header consolidation sends paper metadata to CrossRef (§2.3) |
| `includeRawCitations` | `1` | Raw reference strings kept in the stored TEI (`OQ-003`) |
| `teiCoordinates` | `p`, `head`, `figure`, `biblStruct` | Pages come only from coordinates (§2.4) |
| `generateIDs`, `segmentSentences`, `flavor` | not sent | Random IDs; sentences not needed; flavors flatten the body |

These values are recorded with each document as the parser configuration (`DR-005`).

## 3. `ParsedDocument`

All text fields are `None` when absent, never `""` (`FR-ING-006`, `DR-007`).

| Field | Type | Source in TEI | Notes |
|---|---|---|---|
| `parser_name` | `str` | constant `"grobid"` | |
| `parser_version` | `str` | `teiHeader//appInfo/application[@ident='GROBID']/@version` | `0.9.1` observed |
| `title` | `str \| None` | `fileDesc/titleStmt/title` | |
| `authors` | `list[str]` | `sourceDesc/biblStruct/analytic/author/persName` (forenames + surname) | Empty list when none |
| `doi` | `str \| None` | `sourceDesc/biblStruct/idno[@type='DOI']` | Raw value; normalised by P2-T4 |
| `page_count` | `int \| None` | number of `facsimile/surface` | |
| `passages` | `list[ParsedPassage]` | §4 | In source order |
| `skipped_paragraphs` | `int` | rule R2 | Recorded, never silent |
| `joined_paragraphs` | `int` | rule R1 | Recorded |

## 4. `ParsedPassage`

| Field | Type | Meaning |
|---|---|---|
| `ordinal` | `int` | 0-based position in the order below; unique per document |
| `region` | `"abstract" \| "body" \| "back" \| "caption"` | Where the text came from |
| `back_type` | `str \| None` | GROBID `div/@type` for `back` passages: `annex`, `availability`, `acknowledgement`, `funding`, `conflict`, `contribution` (others kept as given) |
| `section_title` | `str \| None` | Text of the governing `head`; for captions, the figure's label and head (for example "Table 2") |
| `section_number` | `str \| None` | `head/@n` when present (numbered papers only) |
| `text` | `str` | Element text with whitespace collapsed to single spaces; nothing else changed |
| `page_start`, `page_end` | `int \| None` | First and last page in the element's `coords` (§6) |

`section_path` in `FR-ING-007` is `section_number + " " + section_title` when a number exists, otherwise `section_title`: sections are always flat (`OQ-001`), so there is no deeper path.

## 5. Which TEI elements become passages, in this order

| Order | Region | TEI path | Included |
|---|---|---|---|
| 1 | `abstract` | `teiHeader/profileDesc/abstract//p` | All paragraphs |
| 2 | `body` | `text/body/div/p` | All, after rules R1 and R2 |
| 3 | `caption` | `text/body/figure/figDesc` | Non-empty captions; `section_title` from `figure/label` and `figure/head`; table or figure from `figure/@type` |
| 4 | `back` | `text/back/div[@type!='references']//div/p` | All paragraphs, with `back_type`; captions of figures inside back matter follow rule 3 with `region` `caption` |

**Not passages** (still present in the stored TEI artifact):

| Excluded | Reason |
|---|---|
| References (`back//listBibl`) | `OQ-003`: not retrievable in VS-1 |
| Body `note` elements | Footnotes and running headers cannot be told apart (§7) |
| Table cells (`figure/table`), formulas, graphics | Not reliable enough to cite (`OQ-016`) |
| Headings themselves | Kept as `section_title` on passages, not as passages |

### Text rules

- **Text:** concatenation of all text inside the element, whitespace collapsed. In-text citation markers stay as GROBID wrote them (for example "[9][10][11]"; §5.3). Text is **not** quote-normalised; normalisation is applied only when matching quotes (`OQ-013`), so stored passage text stays as derived.
- **R1, join split paragraphs** (body and back only): a paragraph is appended to the **directly preceding** paragraph, with one space, only when both are in the same section, the paragraph starts with a lowercase letter, and the preceding one does not end with `.`, `?`, `!` or `:`. `joined_paragraphs` counts joins.
- **R2, skip paragraphs with no letters** (any region): such a paragraph is not a passage; `skipped_paragraphs` counts it. Observed twice in BERT ("...").
- R1 and R2 are provisional (`OQ-002`): their effect is checked with Recall@5 in Phase 4.

**Why R1 is strict (checked on the five papers, 2026-11-03).** Eight paragraphs start mid-sentence (§5.3), but in seven of them the paragraph directly before is a complete paragraph from elsewhere: GROBID placed other text (another column, a sidebar) between the two halves. R1 therefore joins only 1 of the 8. A looser rule, "join to the nearest earlier paragraph that ends unfinished", was tried: it would pair at least 3 of the 8 fragments with the wrong text (one 25 paragraphs earlier, one reusing a predecessor already taken), and a wrong join produces source text that does not exist in the paper. That breaks evidence integrity, so it is not used. The other fragments stay as separate passages: verbatim text with correct pages, but incomplete sentences. This is a known limitation (`RISK-03`), measured in Phase 4.

**Result on the five papers:** 324 passages (abstract 9, body 239, caption 37, back 39); 1 join; 2 skipped; every passage has `page_start` and `page_end`.

## 6. Pages

- `coords` is a list of boxes `page,x,y,width,height` separated by `;` (§2.4). `page_start` = smallest page, `page_end` = largest page in the element's boxes.
- Captions take the pages of their enclosing `figure` (the `figDesc` has no coordinates; every figure has them).
- A joined passage (R1) takes the first part's `page_start` and the last part's `page_end`.
- No coordinates → both `None`, shown as "page unknown". Never `0` (`DR-007`).
- Coordinates themselves are not stored on passages; they stay in the TEI artifact for later use (for example highlighting in the PDF).

## 7. Outcome and failure reasons (`FR-ING-003`)

A document ends `parsed` only when `parse_tei` returns at least one `body` passage. Otherwise it ends `failed` with one `failure_reason` and a short message without paper text. "Observed" refers to the experiment (§6).

| Stage | Condition | `failure_reason` | Observed? |
|---|---|---|---|
| Validation (before GROBID) | Does not start with `%PDF-` | `not_pdf` | GROBID gave `BAD_INPUT_DATA` for this; caught earlier by us |
| Validation | 0 bytes | `empty_file` | as above |
| Validation | Larger than `MAX_UPLOAD_MB` | `file_too_large` | GROBID has no limit (§6.3) |
| GROBID call | Connection refused | `parser_unreachable` | Yes (`ConnectError`) |
| GROBID call | Connection dropped mid-request | `parser_disconnected` | Yes (`RemoteProtocolError`) |
| GROBID call | No response within `GROBID_TIMEOUT_SECONDS` | `parser_timeout` | No |
| GROBID call | 503 still returned after the retries in P3-T3 (5–10 s apart) | `parser_busy` | Yes (503 under load) |
| GROBID response | 500 `BAD_INPUT_DATA` | `unreadable_pdf` | Yes (corrupt, truncated) |
| GROBID response | 500 `NO_BLOCKS` | `no_text_layer` (likely scanned or image-only) | Yes (image-only, blank) |
| GROBID response | 500 `TOO_MANY_TOKENS` or `TOO_MANY_BLOCKS` | `document_too_long` | Yes (`TOO_MANY_TOKENS`) |
| GROBID response | 500 `TIMEOUT` | `parser_timeout` | No |
| GROBID response | 500 with any other code, or 400 | `parser_error` | No / 400 only for a missing file |
| GROBID response | 204 | `empty_parse` | No |
| Parsing | TEI is not well-formed XML | `malformed_tei` | No |
| Parsing | No `body` passage after R1 and R2 | `empty_parse` | Yes (200 with empty body, §6.3) |
| Restart | Left `processing` when the server stopped | `interrupted` | `FR-ING-010` |

Every failed document keeps its stored file, has no passages, and may be retried (PRD §8.3). Reason codes are lowercase snake_case (`CLAUDE.md` §11).

## 8. Example (synthetic)

```json
{
  "parser_name": "grobid",
  "parser_version": "0.9.1",
  "title": "A Synthetic Paper",
  "authors": ["Ada Example", "Ben Sample"],
  "doi": null,
  "page_count": 2,
  "skipped_paragraphs": 0,
  "joined_paragraphs": 1,
  "passages": [
    {"ordinal": 0, "region": "abstract", "back_type": null, "section_title": null, "section_number": null,
     "text": "We describe a synthetic method.", "page_start": 1, "page_end": 1},
    {"ordinal": 1, "region": "body", "back_type": null, "section_title": "Introduction", "section_number": "1",
     "text": "The method spans a page break and continues here.", "page_start": 1, "page_end": 2},
    {"ordinal": 2, "region": "caption", "back_type": null, "section_title": "Table 1", "section_number": null,
     "text": "Accuracy of the synthetic method.", "page_start": 2, "page_end": 2},
    {"ordinal": 3, "region": "back", "back_type": "availability", "section_title": "Data availability", "section_number": null,
     "text": "All synthetic data are included.", "page_start": 2, "page_end": 2}
  ]
}
```

## 9. Testing (Phase 3)

Small, synthetic or licence-checked TEI fixtures, one per rule: each region; R1 join (including across pages); R2 skip; a passage without coordinates; a document with only abstract and captions (must be `empty_parse`); malformed XML; each GROBID error code mapped to its reason. A determinism test parses the same fixture twice and compares the results.
