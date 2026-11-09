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
