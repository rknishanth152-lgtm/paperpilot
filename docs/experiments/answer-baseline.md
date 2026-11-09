# Real-model answer baseline

| Field | Value |
|---|---|
| Task | P5-T12 (`AC-VS-06`, `AC-VS-07`, `NFR-PRF-001`, `OQ-011`) |
| Date | 2026-11-09 |
| Kind | **Manual real-model run**, labelled as such (`CLAUDE.md` §6.10) |
| Result file | `benchmarks/results/answers-gemini-3.5-flash-lite-20261109T033518Z-d09c9b6.json` |
| Model | `gemini-3.5-flash-lite`, Google Gemini free tier, prompt `answer-v1` |
| Evaluation set | `benchmarks/retrieval_eval_v1.json`, version 1, unchanged |
| Scope | Each question's own paper; unanswerable questions searched all five papers |

## 1. Result

| Measure | Result |
|---|---|
| Answerable questions (16): answered with citations that all validate | **13** |
| Answerable questions: failed citation validation | **0** |
| Answerable questions: said `insufficient` | 3 |
| Answerable questions: expected passage retrieved / cited | 9 / 9 |
| Unanswerable questions (4): said `insufficient` | **4 of 4** |
| Errors or malformed outputs | 0 |
| Mean model time per answer | 2.0 seconds |
| Tokens, 20 answers | 38,236 input, 2,618 output |
| Cost | $0 on the free tier; the same use at paid prices would be about $0.0009 per answer |

**How to read this.** One run of 20 questions over five open-access papers, on one model. It is a coarse baseline, not a general accuracy figure (`RISK-15`). "Validated" means every citation points to a real passage in scope and any quote is in it. **It does not mean the answer is correct or that the passage supports it**: `claim_support` is `not_evaluated`.

## 2. What the answers show

Nine answers (q01, q02, q04, q05, q06, q07, q12, q13, q15) were read beside the passages they cite. The other eleven answers were not read in full.

- **Answers that cited the expected passage held up** in the two read (q02, q15).
- **The 3 `insufficient` answers (q01, q05, q13) were honest.** Search had not found the right passage, so the model said the passages did not cover it instead of guessing. The limit is retrieval (`docs/experiments/retrieval-baseline.md`).
- **Two answers were good without the expected passage.** q04 and q07 cited a different passage in the same paper that states the same finding. "Expected passage cited" therefore undercounts correct answers.
- **q06 passes every check but only partly answers the question.** It asked how often repeat studies succeeded for null results. The answer reports a related figure, from combining original and replication data, and marked itself `sufficient`.
- **q12 was marked `partial`.** Its one statement is true but is about which trials shared data, not what the question asked. Its limitations say so.

q06 is the known gap in practice: a valid citation can back a true statement that does not answer the question. The claim-support label (`FR-EVL-004`) does not measure this, because such a statement is supported. P6-T3 adds a separate label for it.

The question page was then tried in the browser on the same model with q02 and q17. q02 showed its citation as valid, and the displayed passage, page and section matched the database. q17 showed "Not enough evidence" with no statements.

## 3. Not established

- **No real-model failed validation occurred**, so that path is proven only by the fault-injection tests (`AC-VS-08`).
- **The prompt-injection defence was not tested on a real model** (`RISK-08`).
- **No comparison between models.** `gemini-3.6-flash` gave 3 answers, then its free limit stopped it (two validated with the expected passage cited, one `insufficient`). `gemini-3.8-flash` was overloaded and gave none. `OQ-011` stays interim.
- Free-tier limits are shown only inside AI Studio and were not read. `gemini-3.6-flash` stopped after a handful of requests; `gemini-3.5-flash-lite` completed 20 at 30-second intervals.

## 4. Decision

**Interim model: `gemini-3.5-flash-lite`.** It was the only free model that completed the run. It stays interim until a comparison is possible.

## 5. Second run (P6-T1)

The same model and prompt were run again through `tests/evaluation/run_evaluation.py` at commit 9654929, with a clean working tree and the full configuration recorded: `benchmarks/results/answers-gemini-3.5-flash-lite-20261109T040343Z-9654929.json`. The first run's file records `working_tree_clean: false`, because an earlier result file was uncommitted at the time.

| Measure | First run | Second run |
|---|---|---|
| Answerable: all citations valid, with statements | 13 of 16 | 13 of 16 |
| Failed citation validation | 0 | 0 |
| Answerable: said `insufficient` | 3 | 3 |
| Unanswerable: said `insufficient` | 4 of 4 | **3 of 4** |
| Mean model time per answer | 2.01 s | 1.97 s |

Retrieval returned the same passages for all 20 questions, so every difference below comes from the model. No temperature is set, so the provider default applies.

- **q19 (unanswerable, about astronomy) gave a statement**, labelled `partial`. The statement is true about microarray data and its limitations say the passages do not cover astronomy, but it does not answer the question.
- **q12 moved from `partial` to `sufficient`** with the same off-question statement.
- Statement text differed in 9 of 20 answers, q19 included.

So one run's "4 of 4" is not a stable figure, and the model's own sufficiency label should not be read as a measure of quality. Two runs are too few to give a rate.

## 6. Citation reference validity (P6-T2)

Computed from the saved answer files, with no model call, by `tests/evaluation/citation_validity.py`.

| Measure | First run (d09c9b6) | Second run (9654929) |
|---|---|---|
| Citations valid | 16 of 16 | 21 of 21 |
| Answers with statements, validated | 13 of 13 | 14 of 14 |
| Answers without statements (not counted in the rate) | 7 | 6 |
| Model errors | 0 | 0 |
| Failures, any of the four reasons | 0 | 0 |
| Citations that carried a quote | 16 | 21 |

Every citation carried a quote, so each one passed the stricter check. The sample is small, and no failure occurred in either run, so the failure path remains evidenced only by the fault-injection tests.

**This 100% is structural.** It means each citation points to a real, in-scope passage that contains the quoted text. The second run's 14 validated answers include q06 and q19, which pass and still do not answer their questions. Whether passages support statements is measured separately in P6-T3.
