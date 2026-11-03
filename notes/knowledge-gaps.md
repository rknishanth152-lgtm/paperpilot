# PaperPilot Knowledge Gaps: What the Two Transcripts Do and Don't Teach

**Inputs:** your PaperPilot project context (the spec) and your gap-analysis prompt, applied to:
- **FS** = `transcripts/fullstack-rag.txt` (Driftwood Capital document copilot over SEC filings)
- **CC** = `transcripts/claude-code-rag.txt` (eight-module agentic RAG over appliance manuals)

You wrote "the supplied transcript" in the singular and I have two, so I compared both against the spec, and each row says which transcript supports it.

## How to read this

| Tag | Meaning |
|---|---|
| **[T]** | Said or shown in the transcript. |
| **[V]** | Checked in official documentation during this session (details in section 4). |
| **[R]** | My technical recommendation. Not in the transcripts. |
| **[U]** | The transcripts don't show it. |

**Citations:** The transcript files have no timestamps or headings. I cite by step label from `implementation-notes.md` (A1–A19 for FS, B0–B11 for CC) plus a short paraphrase. Those labels follow the order of the video.
**Important limit:** both are speech-only captions. No code is visible. "Teaches how to implement" therefore means the *workflow and design* were demonstrated and explained, not that you can copy code from them.
**Stack divergence:** both builds use Supabase (auth, RLS, storage, hosted Postgres). Your spec asks for plain PostgreSQL, local file storage, and a storage interface. Treat the Supabase parts as optional.

---

## 1. Direct coverage

Only two spec items are covered at the level of "demonstrated end to end with a verified result", and both only at design/workflow level.

| Spec item | Transcript evidence | What it gives you | What it still leaves open |
|---|---|---|---|
| **Req 6: hybrid keyword + semantic retrieval** (build mechanism) | **FS A13:** pgvector semantic search + Postgres full-text search, fused with Reciprocal Rank Fusion, top-K plus ±1 neighbour chunks, adapted from BM25 to Postgres full-text; checked with a smoke script on a filtered question. **FS A14:** an LLM extracts 3–5 keywords because the raw question "will almost never match" in full-text. **CC B8:** hybrid + optional Cohere rerank, confirmed in LangSmith (rerank, RRF and similarity scores shown; earlier run showed only RRF and similarity). | The pipeline shape, the reason for keyword extraction, evidence that rerank can be verified through traces, scoping with filters (ticker/form in FS). | The SQL and index details, any evaluation. See section 2. |
| **Req 7: evidence-grounded answers** (pattern) | **FS A14:** the agent must return a structured Pydantic answer with citations; a validator rejects chunk ids that were never retrieved and requires excerpts copied from retrieved chunks; on failure the user is told no grounded answer was found. | The core contract: structured output, citations as ids, refusal path, a post-check separate from generation. | The three-way distinction the spec requires (supported / interpretation / insufficient). The validator's exact logic is hedged by the speaker ("I believe"). |

Honest caveat: the video says it takes "a day or two" to tune each block, and the developer says he has **not** validated the tools, prompts or validator. Treat these as patterns to rebuild and test, not as proven designs.

---

## 2. Partial coverage

| Spec item | What the transcripts teach | What is missing |
|---|---|---|
| **Req 2 (ingestion workflow only)** | **CC B5:** upload UI, per-user storage folder, document row with status (pending/processing/completed), realtime status, delete cascades to chunks and file; file-type limits. **CC B8:** concurrency limit (3 then 10) after memory hit 92%. | No "failed" status or error recording is described [U] (spec: "must not silently treat failed processing as successful). No PDF validation beyond type/size mentions; the 50 MB limit was in a plan only. Local-disk storage and a storage interface are not shown (they use Supabase Storage). |
| **Req 3: structured extraction** | **CC B7:** LLM extracts document metadata (title, summary, document type, topics, language) using a Pydantic schema stored as JSON in the database; first 8,000 characters only; copied onto chunks; no backfill. | This is *document-level metadata*, not findings. Nothing on methods, datasets, metrics, results; no section-aware extraction of a full paper; no validation-failure handling or retries; no per-field evidence pointer, status, confidence, or human correction. |
| **Req 4: PostgreSQL data model** | **FS A5:** SQLAlchemy models, one file per model, Alembic migration, tables verified in the dashboard, vector column visible. **FS A15:** a citations table linking messages to chunks. **FS A17:** a `document_tables` table (table markdown + JSON). | The spec's model (claims, evidence, methods, datasets, metrics, results, checklist items, corrections) is never designed. No many-to-many claim↔evidence modeling. Source text vs AI interpretation as separate tables (Principle 2) is not discussed. |
| **Req 5: searchable passages** | **FS A12:** Docling HybridChunker (header-aware, token-limited), page number, section, index and token count stored per chunk; one-document dry run first. | Chunking for *papers*: references, headers/footers, equations, two-column layout, captions. The developer himself found table chunks too context-poor and left a fix unbuilt. No overlap or length decision is justified. No stable chunk identity across re-ingestion. |
| **Req 8: citation validation** | **FS A14:** cited chunk ids must belong to the retrieved set; excerpts must be copied from them. | The spec's checks (paper exists, passage exists, passage belongs to paper, page consistent with stored metadata) are not enumerated. Whether the validator is deterministic code or an LLM is unclear [U]. Claim support is not separated from reference validity. |
| **Req 6 (evaluation half)** | — | The spec wants to measure whether hybrid beats keyword or vector alone. Neither transcript measures retrieval (no Recall@k, no gold questions). FS says only "does the pipeline work" and judged by eye. |
| **Testing (spec §5)** | **CC B6:** Playwright browser tests, a regression suite with acceptance criteria, manual two-user isolation test. | Unit, integration and API tests are not shown. The CC suite checks features, not retrieval or grounding quality. |
| **AI provider interface (spec §5)** | **CC B6:** configurable provider, base URL and embedding model through OpenAI-compatible endpoints; embedding provider separate from chat model; embedding model locked once chunks exist. | A defined interface in code that hides provider calls is not shown. |

---

## 3. Missing coverage

| Spec item | Status in the transcripts |
|---|---|
| **Req 1: paper discovery (OpenAlex)** | Not addressed. The only "discovery" is a script that bulk-downloads SEC filings (FS A1): no scholarly metadata, normalization, DOI dedupe or open-access handling. |
| **Req 2: scholarly parsing with GROBID** | GROBID is never mentioned. Docling is used on SEC HTML (FS) and on appliance-manual PDFs (CC); the CC PDF test was a spot check. Nothing on bibliographic metadata, reference extraction, or section structure for research papers. |
| **Req 9: cross-paper comparison** | No comparison matrix, no comparability rules. The Apple "revenue mix 2021–2025" question is just a retrieval question. CC's `analyze_document` sub-agent (B10) handles one document and is the closest *building block*, not comparison. |
| **Req 10: reproducibility checklists** | Not addressed. |
| **Uncertainty states (Principle 6)** | Reported / partially reported / not found / needs review, and "absence of evidence ≠ proof of absence", are not discussed. |
| **Human correction and verification records** | Not addressed. |
| **Evaluation of extraction, citations, comparison and checklists (spec §9)** | Not addressed. Both developers say you should test against data you can fact-check yourself (FS A19 wrap-up) but show no method. |
| **Claim-support checking** | Not addressed. |
| **Deterministic checks as a design principle** | Only a database-level example (CC B9: a read-only Postgres role for text-to-SQL). Not applied to citations. |
| **Local file storage + storage interface** | Not addressed (Supabase Storage used). |
| **GitHub Actions** | Not shown in either. FS deploys with Docker on Railway; CC doesn't deploy. |

---

## 4. Research gaps: specific questions and where to resolve them

I checked these references during this session. [V] marks facts confirmed there. Other items are my recommendations.

| # | Specific question you must answer | Authoritative reference | Small experiment |
|---|---|---|---|
| G1 | What does GROBID return for a paper, and how do I get **sections and page numbers** into my passage table? | GROBID service documentation (GROBID service page on grobid.readthedocs.io). [V] The full-text endpoint is `processFulltextDocument` (POST/PUT, multipart, PDF in `input`). It returns TEI XML. Options include `consolidateHeader` (default 1, uses CrossRef), `consolidateCitations`, `teiCoordinates` (repeatable list of element names such as `figure`, `ref`, `formula`, `s`), `segmentSentences`. Status: 200, **204 no content extracted**, 400, 500, **503 no free threads (retry after 5–10 s)**. I could **not** confirm the coordinate format; read the "Coordinates of structures in the original PDF" page. Note: the page I read was a docs *branch*, so confirm against the current stable docs. | Run GROBID locally on 3–5 real papers. Inspect the TEI. Write a throwaway script that prints each `div`'s heading and paragraph count, and check whether coordinates give a usable page number. |
| G2 | Is GROBID enough, or do I need Docling for tables? | GROBID docs and Docling's official docs. FS A10/A17 is evidence that tables are where Docling failed (duplicate columns, empty cells), on SEC filings. | Hand-pick 5 tables from 3 papers. Compare each parser's output cell by cell. Record pass/fail. |
| G3 | How do I model claim ↔ passage ↔ paper so a claim can't exist without evidence, and corrections are kept? | PostgreSQL documentation on constraints and foreign keys; SQLAlchemy relationship documentation. | Create `passages`, `claims`, `claim_evidence` tables. Insert one claim with two evidence rows. Write one query that reconstructs claim → quote → page → paper. |
| G4 | How do I get **valid structured output** reliably, and how do I handle failures? | Pydantic validation docs; your LLM provider's structured-output (or tool-use) documentation. | Extract datasets and metrics from 3 papers into a Pydantic model. Force a failure (truncate the response) and confirm it is recorded as `failed`, not saved as success. |
| G5 | What chunk size/boundary works for papers? | None authoritative. This is empirical. | Chunk by GROBID paragraph vs. by section. Measure Recall@5 on your gold questions. |
| G6a | How do I build the **keyword half** correctly? | PostgreSQL "Controlling Text Search" page. [V] Four query parsers: `to_tsquery`, `plainto_tsquery`, `phraseto_tsquery`, `websearch_to_tsquery` (the last never raises syntax errors, so it suits raw user input). `ts_rank` and `ts_rank_cd` (cover density) exist. Docs state ranking uses **no global statistics**, so scores aren't comparable across queries. Ranking reads each matching document's `tsvector`, which can be slow on large result sets. | Add a `tsvector` column to passages. Compare `plainto_tsquery` vs `websearch_to_tsquery` vs an LLM keyword step (the FS approach) on 10 questions. |
| G6b | What are the pgvector limits and index choices for my embedding model? | pgvector README (github.com/pgvector/pgvector; I did not fetch it). [V, from a third-party summary, so confirm in the README] `vector` columns: up to 16,000 dimensions unindexed, but **2,000** for HNSW/IVFFlat indexes; `halfvec`: **4,000** indexed. CC B6 used a 4,096-dimension model and changed the column to flexible dimensions, and said an index consequence was unresolved [T/U]. | Pick an embedding model. Create the column with its exact dimension. Build the index. Confirm the index builds, then confirm a nearest-neighbour query uses it. |
| G6c | What does RRF actually compute, and what constant should I use? | The original RRF paper (Cormack, Clarke, Büttcher, 2009). FS used k = 60 [T~]. | Implement RRF in 10 lines of Python on two ranked lists you write by hand. Check the arithmetic. |
| G7 | What is my full citation-validation algorithm? | None authoritative; this is your design. Spec §Req 8 lists the checks. | Build a validator that checks: paper id exists; passage id exists; passage's paper matches; page matches stored page; quote is a substring of the passage. Then feed it 5 fake citations (nonexistent id, wrong paper, wrong page, altered quote, valid) and confirm 4 rejected and 1 accepted. |
| G8 | How do I use OpenAlex for search, abstracts, DOIs and open-access links? | OpenAlex "Work object" documentation. [V] Fields: `doi`, `abstract_inverted_index` (an index of words to positions; **no plain-text abstract**), `authorships` (first 100 authors), `primary_location`, `best_oa_location`, `open_access` (`is_oa`, `oa_url`). **`oa_url` may point to a landing page, not a PDF.** Abstract coverage is not complete. I could not confirm `locations[].pdf_url` or rate-limit/API-key rules on the page I read; check the Location object and API overview pages. | Fetch 10 works for one topic. Rebuild each abstract from the inverted index. Store DOI-normalized records. Count how many have a direct PDF link. |
| G9 | When are two reported results comparable? | None authoritative. My starting rule [R]: comparable only if dataset, split, metric and protocol match; otherwise flag for interpretation. | Hand-build a 3-paper results table with columns: dataset, split, metric, value, quote, page. Write down which pairs you consider comparable and why. |
| G10 | What belongs on a reproducibility checklist? | The Machine Learning Reproducibility Checklist (Pineau et al., used by NeurIPS). Your spec's list closely resembles it. | Fill your 12-item checklist by hand for 3 papers, with a page quote per item. Count "not found" items and re-read the paper to see which were in fact present. |
| G11 | How do I measure retrieval and extraction? | Definitions of Recall@k, precision, recall and F1 (standard, any IR textbook). | Write 20 questions with known answer passages. Compute Recall@5 for keyword-only, by hand if necessary. |
| G12 | How do I run parsing as a job with a visible status? | FastAPI documentation: request files (`UploadFile`) and background tasks. | Upload one PDF. Return immediately. Show status change `pending → processing → completed/failed`. Upload a corrupted PDF and confirm `failed` with a message. |

**Tutorials:** I'm not recommending any. Every gap above is resolved by documentation plus a small experiment. The one gap where documentation can't help is G7/G9/G10: they are design decisions you make from your spec.

---

## 5. Prerequisite concepts

### Essential before the first vertical slice (P0)

| Concept | Plain English | Why PaperPilot needs it | Depth | Exercise |
|---|---|---|---|---|
| **Relational model with foreign keys and migrations** | Tables that point at each other, with rules the database enforces. A migration is a versioned schema change. | Provenance: a passage must belong to a document, which must belong to a paper. | Working | Create `papers → documents → passages` with foreign keys. Try to insert a passage with a nonexistent document and confirm the database refuses. |
| **PDF is layout, not text** | A PDF stores positioned glyphs, not paragraphs or sections. A parser *guesses* structure. | Section and page references only exist if the parser recovers them. | Working | Run GROBID on one paper; compare its sections to what you see in a PDF viewer. |
| **Passage identity** | Every passage needs a stable id and location (paper, section, page, order). | Citations point at passage ids. Re-ingestion must not break them. | Working | Ingest the same paper twice. Decide and test what happens to passage ids. |
| **Embeddings and vector distance** | A model turns text into a list of numbers. Close vectors ≈ similar meaning. | Semantic retrieval; also dimension and index limits. | Working (not the maths) | Embed 5 sentences. Compute the distance between pairs. Check the ones you expect to be close actually are. |
| **Full-text search basics** | Postgres turns text into normalized word entries (`tsvector`) and queries into `tsquery`. | The keyword half, and the first retrieval baseline. | Working | Query your passages three different ways (see G6a). |
| **The answer contract** | The model returns structured output (answer + citation ids + insufficient-evidence flag), not free prose. | You can only validate citations you can parse. | Working | Write a Pydantic model for the answer. Feed it malformed JSON. Confirm the failure is handled. |
| **Reference validity vs claim support** | A citation can point at a real passage that doesn't support the claim. | Spec Requirement 8 says to separate them. | Clear concept | Make a citation to a real but irrelevant passage and show your validator accepts it, then write down why this is not enough. |
| **Evaluation basics (gold set, Recall@k)** | A fixed set of questions with known right answers, so changes can be measured. | Without it you can't tell if retrieval improved. | Working | 20 questions, Recall@5 on keyword search. |

### Learn during implementation

Reciprocal Rank Fusion and reranking; pgvector index types; OpenAlex pagination and rate limits; async jobs; provider abstraction; Docker; structured-extraction prompting; comparability rules; reproducibility checklist wording; GitHub Actions.

---

## 6. MVP simplification

None of these removes evidence provenance or allows unchecked citations.

| Feature | Simplify to | Trade-off | What must eventually be added |
|---|---|---|---|
| Paper discovery | Manual upload of one permitted PDF; enter DOI by hand. | No search or metadata normalization. | OpenAlex search, DOI-based dedupe, open-access/permission handling. |
| PDF parsing | One parser (GROBID per spec) on a few papers, with explicit `failed` status. | Tables may be poor. | A table-handling path if G2 shows a real problem. |
| Structured extraction | 3 fields (datasets, metrics, limitations), each with a quote and page. | Not the full schema. | Remaining fields, section-aware passes, measured F1, user correction. |
| PostgreSQL storage | Plain Postgres in Docker, files on local disk, no Supabase auth/RLS. | Single-user. | Storage interface for object storage; users and permissions later. |
| Chunking | One strategy (GROBID paragraph or section), no overlap at first. | Some answers split across chunks. | Tuned size/overlap, neighbour expansion (FS used ±1), table and reference handling. |
| Keyword retrieval | Postgres full-text first and **alone** for the vertical slice. | Misses paraphrase. | Becomes half of hybrid. |
| Semantic retrieval | Add after the keyword baseline is measured. | Extra model, cost and index. | Index choice per G6b. |
| Hybrid retrieval | Simple RRF of two lists. | Untuned. | Evaluate vs each alone (spec Req 6); rerank only if measured gain. |
| Grounded answers | **One retrieval + one LLM call** with structured output. Skip the agent tool loop. | Cannot self-correct when evidence is thin. FS's loop took about 60 s and roughly $1–2 per query [T]. | Query router / loop only if evaluation shows the single call fails. |
| Citation validation | Deterministic checks only (G7). | Doesn't judge claim support. | Separate claim-support evaluation (automated or human). |
| Cross-paper comparison | Table assembled from already-extracted rows, each cell linked to evidence. | No reasoning about differences. | Comparability labels (direct / contextual / not comparable). |
| Reproducibility checklist | ~5 items, four statuses, evidence per item. | Not a full checklist. | Remaining items; wording that "not found" is not proof of absence. |

**Safe to skip entirely for now:** Supabase/RLS, auth, Realtime, dark mode, Railway deployment, the sub-agent UI, text-to-SQL, web search, local models. Both transcripts spend most of their time there. They are not on your MVP path.

---

## 7. Prioritized gap analysis

| Priority | Requirement | Coverage | Knowledge gap | How to resolve it | When it is needed |
|---|---|---|---|---|---|
| **P0** | Req 2 parsing | Missing (GROBID) | What GROBID returns; how to get sections and pages | **Learn+Build:** G1 experiment | Before schema design |
| **P0** | Req 4 data model | Partial | Passage/claim/evidence relations; stable ids | **Learn+Build:** G3 | Before ingestion |
| **P0** | Req 5 passages | Partial | Chunking for papers; passage identity | **Build:** G5 on 3 papers | Slice step "store passages" |
| **P0** | Req 6 keyword retrieval | Partial | tsvector/tsquery/ranking caveats | **Learn+Build:** G6a | Slice step "retrieve" |
| **P0** | Req 7 answers | Direct (pattern) | Structured answer contract with refusal | **Build:** Pydantic answer model (G4) | Slice step "answer" |
| **P0** | Req 8 citations | Partial | Full deterministic validator | **Build:** G7 with fake citations | Slice step "inspect evidence" |
| **P0** | Evaluation | Missing | A gold set | **Build:** G11 (20 questions, hand-labeled) | Before tuning anything |
| **P1** | Req 2 ingestion | Partial | Failure statuses; PDF validation | **Build:** G12 | Slice reliability |
| **P1** | Req 8 | Partial | Page/quote consistency checks | Extend G7 | Slice reliability |
| **P1** | Uncertainty states | Missing | Distinguish missing, ambiguous, failed, absent | **Learn:** design a status enum | Before extraction |
| **P2** | Req 1 discovery | Missing | OpenAlex fields, DOI dedupe, OA links | **Learn+Build:** G8 | After persistence |
| **P2** | Req 3 extraction | Partial | Findings schema, evidence quotes, validation | **Build:** G4 on 3 fields | After slice |
| **P2** | Req 6 semantic + hybrid | Direct (pattern) | Embedding dim, index limits, RRF, evaluation | **Learn+Build:** G6b, G6c, G11 | After keyword baseline |
| **P2** | Req 9 comparison | Missing | Comparability rules | **Design:** G9 | After extraction |
| **P2** | Req 10 reproducibility | Missing | Checklist content and statuses | **Design:** G10 | After extraction |
| **P3** | Human correction records | Missing | Schema for verification/corrections | Design when UI exists | Post-MVP |
| **P3** | Claim-support evaluation | Missing | Automated or human judging | Design after reference validity works | Post-MVP |
| **P3** | CI, object storage, provider abstraction | Partial/Missing | Interface design | Spec §5 | Post-MVP |

---

## 8. Minimal learning roadmap

Each stage ends with a go/no-go condition. Do the learning and the building together: stages are small.

| Stage | Concept | Reference | Practical exercise | Expected result | Move on when |
|---|---|---|---|---|---|
| **1. Parse papers** | PDF structure; TEI output | GROBID service docs (G1) | Parse 3–5 real papers; print headings, paragraphs and pages | A short table: paper → sections → paragraph counts → page availability | You know whether you can get a page number for every paragraph, and you know the parser's failure modes (204, 503, empty output) |
| **2. Provenance schema** | Foreign keys, migrations, stable ids | PostgreSQL constraints docs; your migration tool's docs | Create `papers`, `documents`, `passages`; load one parsed paper; try illegal inserts | Database rejects orphan passages; re-ingestion keeps ids stable | A passage query returns paper, section, page, text |
| **3. Gold set + keyword retrieval** | tsvector/tsquery; Recall@k | PostgreSQL text-search docs (G6a) | Write 20 questions with known passages. Retrieve with FTS | A measured Recall@5 number (real, from your run) | You have a baseline number and a list of failures |
| **4. Answer contract + validator** | Structured output; reference validity | Pydantic docs; your provider's structured-output docs | One retrieval + one LLM call; validator from G7; fault-injection test | Fake citations rejected; "insufficient evidence" returned for out-of-corpus question | **Vertical slice done**: upload → parse → store → retrieve → answer → inspect evidence |
| **5. Semantic + hybrid** | Embeddings, pgvector limits, RRF | pgvector README (G6b); RRF paper | Add embeddings, then RRF; rerun the gold set | Recall@5 for keyword / vector / hybrid | You can state which wins on your data |
| **6. Small extraction** | Schema validation; evidence quotes | Pydantic docs (G4) | Extract 3 fields from 3 papers; compare to hand labels | Field-level precision/recall (measured) and failure statuses | Every extracted item has a quote and page, and failures are visible |
| **7. Comparison + checklist** | Comparability; reporting checklist | ML Reproducibility Checklist (G10); your rules from G9 | Hand-build both for 3 papers, then generate from extracted rows | Matrix and checklist where every cell has evidence or an explicit status | Hand-built and generated versions agree or the differences are explained |
| **8. Discovery** | OpenAlex works | OpenAlex Work object docs (G8) | Fetch 10 works, rebuild abstracts, dedupe by DOI | Stored metadata with OA link availability counts | Duplicates are merged; unavailable PDFs are handled without error |

**What to postpone:** everything in the "safe to skip" list in section 6, plus the knowledge graph, research-gap discovery, multi-agent work, and cloud deployment (spec §8 also defers these).

---

## What I could not confirm

- GROBID's exact coordinate format and current-stable parameter list (the docs page I read was a branch).
- OpenAlex rate limits, API-key requirements and `locations[].pdf_url`.
- pgvector's limits directly from its README (I relied on a third-party summary).
- Whether either transcript's validator is deterministic code or an LLM call.
- Nothing in this file has been tested. No retrieval or extraction results are claimed.
