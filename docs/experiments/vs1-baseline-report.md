# VS-1 baseline report and acceptance review

| Field | Value |
|---|---|
| Tasks | P6-T5, P6-T6 (work package R1; `NFR-PRF-001`, `RISK-15`, `AC-VS-10`) |
| Date | 2026-11-09 |
| Corpus | 5 open-access papers (CC BY), 324 passages, not committed |
| Evaluation set | `benchmarks/retrieval_eval_v1.json`, version 1, 20 questions (16 answerable, 4 unanswerable), reviewed before the first run |
| Model | `gemini-3.5-flash-lite`, Google Gemini free tier, prompt `answer-v1`, provider default temperature. **Manual real-model runs** |
| Main run | Commit 9654929, clean working tree |

All figures come from saved files in `benchmarks/results/`. They are a coarse baseline from a small set, not general accuracy figures (`RISK-15`). **No targets are set from this baseline.**

## 1. Summary

| Measure | Result | Sample |
|---|---|---|
| Recall@5, all papers searched | **8 of 16 (50%)** | 16 answerable questions |
| Recall@5, within the question's paper | 9 of 16 (56%) | 16 answerable questions |
| Citations that pass validation | 21 of 21 | 14 answers with statements |
| Answerable questions answered with all citations valid | 13 of 16 | One run |
| Answerable questions that said `insufficient` | 3 of 16 | One run |
| Unanswerable questions that said `insufficient` | **3 of 4** (first run: 4 of 4) | Two runs |
| Claim support, developer's current labels | 20 of 20 | 20 statements, one labeller |
| Statement fully answers the question, current labels | **12 of 20 (60%)** | 20 statements, one labeller |
| Mean model time per answer | 1.97 s | 20 answers |
| Cost | $0 on the free tier; about $0.00095 per answer at paid prices | 20 answers |

**Main finding.** Citations are reliably real, and passages generally back the statements made from them. The weak points are finding the right passage (Recall@5 of 50%) and answering the actual question (8 of 20 supported statements only partly answer it or do not answer it).

## 2. Retrieval

Keyword full-text search, `k = 5`, no model involved. Result files: `retrieval-20261108T173245Z-368fd83.json`, `retrieval-20261109T035333Z-9654929.json`, `retrieval-20261109T040351Z-9654929.json`.

- The three runs, all from clean working trees, have identical configuration, summaries and per-question results. Retrieval is repeatable on unchanged data and settings.
- All 8 misses are vocabulary mismatches (`docs/experiments/retrieval-baseline.md` §2). The questions were deliberately paraphrased, which makes this a hard test.

## 3. Answers

Two complete runs, same model and prompt, identical retrieval for all 20 questions.

| Measure | First run (d09c9b6) | Second run (9654929) |
|---|---|---|
| Working tree clean | No (an uncommitted result file) | Yes |
| Answerable: statements with all citations valid | 13 of 16 | 13 of 16 |
| Answerable: failed citation validation | 0 | 0 |
| Answerable: said `insufficient` (q01, q05, q13) | 3 | 3 |
| Answerable: expected passage retrieved / cited | 9 / 9 | 9 / 9 |
| Unanswerable: said `insufficient` | 4 of 4 | 3 of 4 |
| Unanswerable: gave statements | 0 | **1 (q19)** |
| Errors or malformed outputs | 0 | 0 |

The same retrieved passages gave different answers between runs, so the model's own `evidence_sufficiency` label is not a measure of quality. Two runs are too few to give a stable rate. Details and readings of individual answers are in `docs/experiments/answer-baseline.md`.

## 4. Citation reference validity

| Measure | First run | Second run |
|---|---|---|
| Citations valid | 16 of 16 | 21 of 21 |
| Answers with statements, validated | 13 of 13 | 14 of 14 |
| Answers without statements (not counted) | 7 | 6 |
| Failures by any of the four reasons | 0 | 0 |

Every citation carried a quote. **This 100% is structural**: each citation points to a real, in-scope passage containing the quoted text. It does not show that the passage supports the statement. No failure occurred on a real model, so the failure paths are evidenced by fault-injection tests only.

## 5. Claim support (human labels)

All 20 statements from the second run, labelled by the developer on 2026-11-09 under `benchmarks/claim_support_guide_v1.md`.

| Measure | First labels | **Revised labels (current)** |
|---|---|---|
| Claim support | 19 of 20 (95%) | **20 of 20 (100%)** |
| Fully answers the question | 14 of 20 (70%) | **12 of 20 (60%)** |
| `partly` / `no` for answering the question | 5 / 1 | 7 / 1 |
| Supported but not fully answering | 5 | 8 |
| Result file | `claim-support-20261109T093335Z-9e8e8c5.json` | `claim-support-20261109T095647Z-9e98060.json` |

**Read both columns.** Three labels changed after the labeller saw the first result and the assistant's notes on q06 and q12: S11 and S15 (`yes` to `partly`) and S18 (`not_supported` to `supported`). All three moved towards those notes, so the revised labels are not independent of them. The first labels are the independent reading.

One run of one model, one labeller, 20 statements. 20 of 20 does not show that every statement is supported. It shows agreement with one person.

## 6. Latency and cost

| Measure | First run | Second run |
|---|---|---|
| Model time per answer: mean / median / max | 2.01 / 1.83 / 3.08 s | 1.97 / 1.87 / 3.26 s |
| Whole answer, retrieval included: mean / max | 2.04 / 3.10 s | 2.02 / 3.33 s |
| Tokens per answer, input / output | 1,912 / 131 | 1,912 / 151 |
| Model calls, 20 answers | 20 | 20 |
| Actual cost | $0, free tier | $0, free tier |
| At paid prices ($0.30 input, $2.50 output per million tokens, read 2026-11-09) | $0.00090 per answer | $0.00095 per answer |

Measured one request at a time, with pauses for free-tier limits, on one machine. Not a load test.

## 7. Known limitations

**Measurement**
- 20 questions, 5 papers, one model; all rates are coarse.
- `OQ-011` remains interim: no model comparison completed because of free-tier limits.
- A real-model citation failure has not occurred, and prompt injection has not been tested on a real model (`RISK-08`); both are covered by fault-injection tests with the fake model only.

**Answering and retrieval**
- Keyword search misses paraphrased questions. Work packages R2 to R4 measure whether hybrid retrieval helps.
- Unanswerable questions are not always refused: q19 gave a cited statement in one of two runs (§8, `AC-VS-07`).
- An answer drawn from the parsed part of a mixed selection does not mention the documents skipped.

**Parsing (GROBID output, stored unmodified, `DR-002`)**
- Broken ligatures on one paper, figure or table text taken as prose, one caption mixed with body text, and non-headings used as section titles (`progress.md` §6.12).
- Table cells are not reliable enough to cite (`OQ-016`). Scanned PDFs are detected and rejected, with no OCR.

**System**
- A database failure during ingestion leaves a document `processing` until the next server start, when recovery marks it `interrupted` so it can be retried. Recovery assumes one server process.
- Local, single-user, no authentication; must not be exposed to a network (`NFR-SEC-006`).
- Keyboard, screen-reader and reduced-motion checks on the question page are pending (R10).

## 8. VS-1 acceptance review

Re-run on 2026-11-09 at commit 90f4944: 883 backend tests passed; 44 frontend tests passed; `ruff`, `mypy`, `alembic check` and the frontend production build clean.

| Criterion | Verdict | Evidence |
|---|---|---|
| `AC-VS-01` valid PDF reaches `parsed` or `failed`, never stuck | **Met** | Five real papers reached `parsed` (`progress.md` §6.12). `tests/integration/test_reliability.py` covers recovery. A database failure needs a restart to recover (§7) |
| `AC-VS-02` three real papers, structure view, manual observations | **Met** | Five papers, 324 passages, observations in `progress.md` §6.12 |
| `AC-VS-03` failure cases produce the documented reason and no passages | **Met**, see note | Parser failures and unusable output: `test_ingestion_pipeline.py`. Invalid and empty files: `test_rejected_uploads_create_nothing`. Real GROBID outage: `progress.md` §7, 2026-11-08 |
| `AC-VS-04` same file twice gives one document and one passage set | **Met** | `test_same_file_twice_gives_one_document_and_one_passage_set`; real re-upload of all five, 2026-11-08 |
| `AC-VS-05` scoped, ranked retrieval; no match is empty | **Met** | `test_keyword_retrieval.py` |
| `AC-VS-06` answerable question returns statements with valid citations | **Met** | 13 of 16 in both runs, none failed validation |
| `AC-VS-07` unanswerable question returns `insufficient`, no confident factual statement | **Not met in every run** | q17, q18 and q20 met it in both runs. q19 met it in the first run. In the second it returned `partial` with one cited statement, and its limitations said the passages do not cover the question |
| `AC-VS-08` fault-injection cases | **Met** | `tests/integration/test_answering_faults.py` covers each listed case |
| `AC-VS-09` Recall@5 computed, result file exists | **Met** | §2 |
| `AC-VS-10` evidence recorded with dates | **Met** | This report and `progress.md` §7 |

**Note on `AC-VS-03`.** The criterion says each case produces `failed`. Under `FR-ING-001`, invalid and empty files are rejected at upload with a documented error, before any document exists, so they never reach `failed`. No passages are created. This follows the requirement and is recorded here as a difference in wording.

**Note on `AC-VS-07`.** `FR-QA-004` also says an out-of-corpus question does not produce a cited factual answer, which q19 did once. The answer was labelled `partial`, was not marked `sufficient`, and said what it could not cover, but the statement should not have been made. An earlier entry in `progress.md` recorded this criterion as evidenced from the first run alone.

**Definition of done for VS-1**

| Item | Verdict | Evidence |
|---|---|---|
| Migrations apply to an empty database | Met | `test_migration_applies_to_an_empty_database` |
| Tests run from a documented command | Met | `README.md` |
| README states how to run GROBID, PostgreSQL, backend and frontend | Met | `README.md` |
| Known limitations written down | Met | §7 |
| Developer acceptance | **Pending** | |

## 9. How to reproduce

```bash
uv run python -m tests.evaluation.run_evaluation --pause 30
```

This is a manual real-model run that needs a configured key and sends questions and retrieved passages to the provider. Each run saves new dated files. Commands for citation validity and claim support are in `tests/evaluation/README.md`.
