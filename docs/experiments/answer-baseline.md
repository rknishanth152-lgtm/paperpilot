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

q06 is the known gap in practice: a valid citation can back a true statement that does not answer the question. Phase 6 measures this with human labels (`FR-EVL-004`).

## 3. Not established

- **No real-model failed validation occurred**, so that path is proven only by the fault-injection tests (`AC-VS-08`).
- **The prompt-injection defence was not tested on a real model** (`RISK-08`).
- **No comparison between models.** `gemini-3.6-flash` gave 3 answers, then its free limit stopped it (two validated with the expected passage cited, one `insufficient`). `gemini-3.8-flash` was overloaded and gave none. `OQ-011` stays interim.
- Free-tier limits are shown only inside AI Studio and were not read. `gemini-3.6-flash` stopped after a handful of requests; `gemini-3.5-flash-lite` completed 20 at 30-second intervals.

## 4. Decision

**Interim model: `gemini-3.5-flash-lite`.** It was the only free model that completed the run. It stays interim until a comparison is possible.
