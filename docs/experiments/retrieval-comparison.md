# Retrieval comparison

| Field | Value |
|---|---|
| Task | R4 (P8-T6, P8-T7; `FR-RET-007`) |
| Date | 2026-11-09 |
| Kind | **Manual real-model run**: each evaluation question is sent once to the embedding provider |
| Evaluation set | `benchmarks/retrieval_eval_v1.json`, version 1, unchanged |

## 1. Rule fixed before the first run

Written and committed before any result existed, and coded in `recommended_method`.

- Scored question count is 16, so a gain of one question is not meaningful.
- A method qualifies only if it finds **at least 2 more** expected passages than keyword across all papers, and **no fewer** within the question's paper.
- Among those that qualify, the highest count across all papers wins, then the highest within the paper, then hybrid, because it still answers from keyword search when embeddings fail.
- If none qualifies, the default stays keyword.

Settings fixed before the first run: `k = 5`, `gemini-embedding-2` at 768 dimensions, hybrid with 20 candidates per method and a fusion constant of 60. These values are not to be tuned on this set.

## 2. Result

Two runs from clean commit e97811d: `retrieval-comparison-20261109T104807Z-e97811d.json` and `retrieval-comparison-20261109T104923Z-e97811d.json`.

| Method | Recall@5, all papers | Recall@5, within the question's paper | Mean reciprocal rank, all papers |
|---|---|---|---|
| Keyword | 8 of 16 | 9 of 16 | 0.236 |
| **Semantic** | **16 of 16** | **16 of 16** | **0.885** |
| Hybrid | 11 of 16 | 12 of 16 | 0.568 |

Semantic ranked the expected passage first for 13 questions, second for 1 and third for 2. Hybrid scored lower than semantic because fusion gave weight to keyword results that were wrong.

**Checks on a result this high.** The two runs are identical. Keyword results are identical to the earlier baseline, so the set and harness did not change. Only 2 of the 16 questions accept more than one passage.

**How to read 16 of 16.** The questions were written against these five papers and deliberately reworded, which is the case semantic search is built for. It shows the keyword failure was vocabulary, as the baseline analysis found. It is not a general accuracy figure (`RISK-15`).

**A score cannot show that a question is answerable.** The top semantic score was 0.73 to 0.87 for answerable questions and 0.71 to 0.82 for unanswerable ones.

## 3. Decision

By the rule in §1, **semantic becomes the default** (`AD-017`). Hybrid qualified but scored lower. Passages in a selection with missing embeddings use keyword search for the whole selection, and the response names the method. New uploads are not embedded automatically, so that no paper's full text leaves the machine without running the embedding job. A provider failure is an explicit error.

## 4. Effect on answers

Same model and prompt (`answer-v1`), from clean commit 3d8a7fb, against the two keyword runs in `docs/experiments/vs1-baseline-report.md`.

| Measure | Keyword (2 runs) | Semantic run 1 | Semantic run 2 |
|---|---|---|---|
| Answerable: expected passage retrieved | 9 of 16 in each | 16 of 16 | 16 of 16 |
| Answerable: expected passage cited | 9 of 16 in each | 15 of 16 | 15 of 16 |
| Answerable: said `insufficient` | 3 in each | **0** | **0** |
| Answerable: failed citation validation | 0 in each | 2 | 1 |
| Unanswerable: said `insufficient` | 4 of 4, then 3 of 4 | **4 of 4** | **4 of 4** |
| Citations valid | 16 of 16, then 21 of 21 | 28 of 30 | 27 of 28 |
| Mean model time per answer | 2.01 s, 1.97 s | 4.88 s | 5.32 s |
| Whole answer, mean | 2.04 s, 2.02 s | 5.66 s | 6.18 s |
| Paid-equivalent cost per answer | $0.00090, $0.00095 | $0.00093 | $0.00090 |

Result files: `answers-gemini-3.5-flash-lite-20261109T110614Z-3d8a7fb.json`, `answers-gemini-3.5-flash-lite-20261109T111824Z-3d8a7fb.json`.

- **The citation check caught real model errors for the first time.** All 3 failures are `quote_mismatch`: q08 changed the case of a quote's first letter, and q09 joined parts of a passage with an ellipsis, in both runs. These answers are returned marked `failed`. The rejections are correct; the quotes are not exact.
- **Answers are slower.** Retrieval and embedding add about 0.8 s, and model time rose by about 3 s even though input tokens fell. The cause was not established, and free-tier timing varies.
- **Not re-measured:** claim support and "answers the question" labels apply to the earlier keyword answers. These answers have not been labelled.

## 5. The planned prompt fix was not applied

R4 planned a prompt fix for the `AC-VS-07` exception (q19 stating something on an unanswerable question). On semantic retrieval with the unchanged prompt, all 4 unanswerable questions were refused in both runs, so there is no failure left to fix or measure against. A change now could not be shown to help, and could cause wrong refusals where there are none today. `answer-v1` stays. Two runs are still few, so this is a recorded observation and not proof that the problem is gone.
