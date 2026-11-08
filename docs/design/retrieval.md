# Keyword retrieval: full-text search configuration

| Field | Value |
|---|---|
| Task | P4-T1 (`FR-RET-001`, `FR-RET-003`, `OQ-004`) |
| Status | **Interim choice**, 2026-11-08. `OQ-004` is settled by the evaluation set (P4-T7), which does not exist yet |
| Source | PostgreSQL 18 documentation, chapters 12.1, 12.2, 12.3 and 12.11, read 2026-11-08. Local server: PostgreSQL 18 |

## 1. The choice

| Decision | Interim choice | Alternative and why not |
|---|---|---|
| Language configuration | `english`, always named explicitly | `simple`: no stemming and no stop words (§3) |
| Search representation | Stored generated column from `to_tsvector('english', text)` with a GIN index (the pattern on the documentation's page 12.2). Passage text only | Adding section titles: some are wrong (`progress.md` §6.12). Can be tested in P4-T7 |
| Query parsing | `plainto_tsquery('english', :q)`, with its ANDs changed to ORs: `replace(plainto_tsquery('english', :q)::text, ' & ', ' \| ')::tsquery` | `websearch_to_tsquery`: ANDs terms, and treats user text as operators (§2, §3) |
| Ranking | `ts_rank(vector, query)`, normalisation 0 | Length normalisation favours fragments. `ts_rank_cd`: no evidence either way (§3) |
| Tie-break | Passage id, so equal scores have a fixed order (`FR-RET-002`) | — |

**Implemented:** the search column and index (P4-T2, migration `e3ab5ad233d7`); query parsing, ranking and scope in `backend/app/services/retrieval/keyword.py` (P4-T3).

**Scope rules (P4-T3).** Only `parsed` documents are searched. `None` means no restriction by that field. An empty collection means nothing is in scope, never everything. When document and paper scope are both given, a passage must satisfy both. An unknown id gives an empty list.

**Input handling (P4-T3).** NUL characters and unpaired surrogates are removed, because they carry no meaning and the driver rejects them. A question over `MAX_QUERY_CHARS` (default 2,000) raises `QueryTooLongError` with code `query_too_long`. The roadmap says "no exception on arbitrary input"; this is the one deliberate exception. The PRD lists a very long query as a failure case with a structured error, and truncating would silently answer a different question. No other input raises.

## 2. What the documentation says

- Only `websearch_to_tsquery` is documented as never raising syntax errors. `to_tsquery` does raise them. Nothing is stated either way for `plainto_tsquery`.
- `plainto_tsquery` ignores operators and punctuation in the input and joins words with AND. `websearch_to_tsquery` joins with AND, and also reads quotes as phrases, `or` as OR, and a dash as NOT.
- A configuration name must be given for an index to be usable, so that it does not depend on `default_text_search_config`.
- `ts_rank` measures how often matching lexemes occur. `ts_rank_cd` also uses their proximity and needs positions.
- Scores use no global information, so they are only comparable within one query. **Do not show them as percentages or confidence.**
- Ranking reads the vector of every matching row, so it can be slow on large result sets. This does not matter at the current size.
- Limits: lexeme under 2 KB; tsvector under 1 MB; positions up to 16,383; at most 256 positions per lexeme; tsquery under 32,768 nodes. The longest passage in the five real papers is 2,843 characters, far below these.

GIN versus GiST was not read. GIN follows the documentation's own example; revisit only with a measured reason.

## 3. What the probes showed

Read-only queries on the development database: 324 passages from five real papers, six probe queries (§5). The probes are a sanity check on a handful of queries, **not an evaluation**, and no accuracy claim follows from them.

**Passages matched, of 324:**

| Probe | `english` AND | `english` OR | `simple` AND | `simple` OR |
|---|---|---|---|---|
| 1 | 13 | 167 | 0 | 285 |
| 2 | 1 | 121 | 0 | 121 |
| 3 | 4 | 147 | 0 | 285 |
| 4 | 1 | 116 | 0 | 265 |
| 5 | 1 | 163 | 0 | 256 |
| 6 | 3 | 80 | 1 | 245 |

`websearch_to_tsquery` and `plainto_tsquery` matched the same counts on these probes.

- **AND is too strict for questions.** A passage must contain every content word, so a supporting passage that words one term differently is lost. OR finds candidates and leaves ordering to ranking.
- **`simple` keeps stop words.** With AND almost nothing matches; with OR nearly every passage matches on words like "the".
- **`websearch_to_tsquery` reads a question as operators.** `non-animal -experiments` produced a NOT on `experi`, and the word `or` becomes an operator. `FR-RET-003` asks that the question be treated as data.
- **Length normalisation promotes very short passages.** Normalisation 2 ranked a passage under 100 characters first in 5 of the 6 probes, and normalisation 1 in 3 of 6. Without normalisation, the top passage was over 1,000 characters in all 6.
- **`ts_rank` and `ts_rank_cd` overlap on these probes.** Neither was checked against what a correct answer would be. `ts_rank` is the interim default only because nothing here separates them; compare in P4-T7.

**Hostile input** (empty, spaces, punctuation, stop words only, SQL text, tsquery operators, unbalanced quotes, backslashes, a URL with `&`, Unicode, one 3,000-character token) returned rows or an empty result with all three parsers, with no errors. Two inputs raised errors with **every** parser, including `websearch_to_tsquery`:

| Input | Error | Required in P4-T3 |
|---|---|---|
| 40,000 words | `stack depth limit exceeded` | Limit the query length, as a setting, and reject longer input with a structured error |
| A NUL character | Driver `DataError` | Remove or reject NUL before the query |

"Never raises syntax errors" does not cover size or driver errors. Because the OR form casts text back to a tsquery, which the documentation does not guarantee for arbitrary input, the P4-T4 tests must cover these inputs.

## 4. Known weakness: broken ligatures

In p3, a search for "findings" matches 6 passages, while 17 contain the split form `fi ndings`. A pattern for split `fi`/`fl` words matches 25 passages in p3 and none in the other four papers.

**Plan:** leave the search text as stored for the baseline. Then test a repair in the search representation only, never in `passages` (`DR-002`), as a before/after in P4-T7 with the evaluation set held fixed.

## 5. Probe queries (excluded from the evaluation set)

These were seen with their results, so P4-T5 must not use them or close paraphrases:

1. What pre-training tasks does the model use?
2. How many experiments were replicated?
3. Does sharing data increase the citation rate?
4. What proportion of journals require data availability?
5. positive predictive value of research findings
6. statistical significance and p-values
