# Keyword retrieval baseline

| Field | Value |
|---|---|
| Task | P4-T7 (`FR-EVL-002`, `AD-005`, `OQ-002`, `OQ-004`) |
| Date | 2026-11-08 |
| Result file | `benchmarks/results/retrieval-20261108T173245Z-368fd83.json`, a saved harness run from a clean commit |
| Evaluation set | `benchmarks/retrieval_eval_v1.json`, version 1, reviewed, unchanged after results were seen |
| Configuration | `docs/design/retrieval.md` |

## 1. Result

| Measure | Result |
|---|---|
| Recall@5 across all five papers | **8 of 16 (50%)** |
| Recall@5 within the question's own paper | 9 of 16 (56%) |
| Unmatched expectations | 0 |
| Unanswerable questions | 4, listed but not scored |

**How to read this.** It is a coarse baseline from 16 scored questions over five open-access papers, not a general accuracy figure (`RISK-15`). One question moves the score by more than 6 points. The questions were deliberately worded differently from the papers, so that keyword search would not be helped by copied phrases; that makes this a hard test, and a person using the paper's own words would likely see better results. Hits and misses say whether a passage was retrieved, not whether a generated answer would be correct.

## 2. Every miss

| Question | Rank of the right passage | Cause | What differs |
|---|---|---|---|
| q01 optimizer and learning rate | 27 | Vocabulary mismatch; common terms | The passage says `Adam`, not "optimizer". `bert`, `model` and `pre-train` are common in the paper but absent from this passage |
| q04 how much effects shrink | 25 | Vocabulary mismatch | "shrink", "repeated" against "smaller", "replications" |
| q05 one unsuccessful repeat | 38 and 64 | Vocabulary mismatch | "unsuccessful repeat", "wrong" against "failure to replicate", "disconfirm" |
| q06 repeat studies with no effect | 27 | Vocabulary mismatch | "repeat studies", "no effect" against "replications", "null effects" |
| q07 animals reproducing | 10 | Vocabulary mismatch | "studies", "reproduce" against "experiments", "replicate" |
| q12 properties linked to being cited | 22 | Vocabulary mismatch, stemming | "properties", "cited" against "features", "citation": `cite` and `citat` are different stems |
| q13 caveat about causation | 13 | Vocabulary mismatch | "caveat", "concluding" against "limitation", "imply" |
| q15 federal grants | 10 (5 within its paper) | Vocabulary mismatch | "federal grants", "post" against "government funding", "depositing" |

**All 8 misses are vocabulary mismatches.** None was traced to a passage boundary or a labelling error, and every expected quote was found. Query wording is the same cause seen from the other side: these are ordinary paraphrases, so the wording is not wrong. Long passages also ranked first in several misses, because without length normalisation they can match more of a question's words.

## 3. Other findings

- **Unanswerable questions cannot be told apart by score.** Their top scores were 0.032 to 0.055; the correct passages that were hits scored 0.011 to 0.045. A score threshold cannot decide "not enough evidence" (`FR-QA-004`). That decision must not rest on the retrieval score.
- **Split ligatures cost nothing on this set.** All three p3 questions were hits. The defect still exists (`retrieval.md` §4), but this set shows no measurable effect.
- **`OQ-002`, passage rules.** No miss came from where a passage starts or ends, so the provisional rules stand. With 16 questions this does not prove them right.

## 4. Alternatives, with the set held fixed

**Exploratory, not metrics.** From `scripts/retrieval_variants.py`, saved in `benchmarks/results/variants-*.json`. It reproduces the baseline's 8 and 9, then changes one thing at a time. These variants were tried after the baseline was seen, so choosing one by score would be tuning on the evaluation set.

| Variant | All papers | Own paper | Gained | Lost |
|---|---|---|---|---|
| Baseline: `ts_rank`, words ORed | 8 | 9 | — | — |
| Words ANDed | 0 | 0 | — | all 8 |
| `ts_rank_cd` | 9 | 10 | q07, q12 | q08 |
| `ts_rank`, normalisation 1 | 6 | 7 | q15 | q02, q09, q16 |
| `ts_rank`, normalisation 2 | 0 | 2 | — | all 8 |
| `ts_rank_cd`, normalisation 1 | 7 | 9 | q07, q12 | q02, q08, q09 |
| Split-ligature repair | 8 | 9 | — | — |
| Section title in the vector | 7 | 10 | — | q09 |

## 5. Decision

**No change to the configuration.** `OQ-004` stays an explicitly documented interim choice.

- ORing the words is supported: ANDing them retrieved nothing relevant.
- Length normalisation is rejected on this evidence.
- `ts_rank_cd` gained one question net. One question on a set this small is noise, so it does not justify a change. It is the first thing to re-test when the set grows.
- Ligature repair showed no benefit here, so no repair is added now.

**What would help** is matching meaning rather than words, which is what semantic retrieval is for (`AD-005`, `FR-RET-005`, Phase 8). This baseline is what that work must beat. Synonym dictionaries and LLM query expansion stay deferred.
