# Embeddings

| Field | Value |
|---|---|
| Task | R2 (P8-T1 to P8-T3; `FR-RET-005`, `OQ-012`, `AD-011`, `AD-014`) |
| Date | 2026-11-09 |
| Sources | Google's Gemini API embeddings, rate-limits, pricing, API reference and terms pages (the `ai.google.dev` addresses now redirect to `aistudio.google.com`), and the pgvector README, all read 2026-11-09 |

## 1. Decisions

| Decision | Choice | Reason |
|---|---|---|
| Model | `gemini-embedding-2` | Google's latest embedding model, free on the free tier, and the same key as answers |
| Dimensions | 768 | One of Google's recommended sizes. Google normalises this size automatically for this model. Enough for 324 passages at a quarter of the storage of 3,072 |
| Storage | Table `passage_embeddings`, one row per passage and model | `AD-014`. Passages stay immutable source text (`DR-002`) |
| Column type | `vector` without a fixed size, plus `dimensions` and a check that they agree | A different model needs no migration |
| Provenance | `model`, `text_format`, `dimensions`, `created_at` on every row | `DR-005`. `text_format` names how the text was written for the model |
| Index | **None; search is exact** | See §2 |
| New dependency | None | httpx is already used. `pgvector-python` is not needed for one small column type |
| API key | `LLM_API_KEY` | Same provider, so no new secret |

## 2. Why there is no approximate index

pgvector applies filters after an approximate index is scanned, so a search scoped to one paper could return too few results unless iterative scans are tuned. The README says a table scan may be faster on a small table, and exact search is the default without an index. With 324 passages, exact search is simple and gives exact, repeatable results. An HNSW index can be added by migration if the corpus grows and measured latency justifies it. pgvector's HNSW limit for `vector` is 2,000 dimensions, so 768 stays within it.

## 3. How text is sent

`gemini-embedding-2` does not accept the `task_type` field. Google asks for the task to be written in the input.

| Use | Text sent |
|---|---|
| Passage | `title: {paper title} \| text: {passage}`, with `title: none` when the title is unknown |
| Query | `task: search result \| query: {question}` |

Requests go to `POST /v1beta/models/gemini-embedding-2:batchEmbedContents` with the `x-goog-api-key` header and `output_dimensionality`.

## 4. Failure handling

- Provider failures use the same specific errors as answering, with no provider text attached.
- Every response is checked: number of vectors, size of each vector, finite values, not all zeros. Anything else is refused and nothing from that batch is stored.
- Each batch is saved before the next is sent. A stopped run reports its reason and how many passages are still missing, and running it again continues.
- If this model's stored rows have another size, the job refuses to start, before anything is sent.
- `count_missing_embeddings` and `scripts/embed_passages.py --check` report missing embeddings, so they are not skipped silently.

## 5. What the documentation does not settle

- **Free-tier rate limits for embeddings** are shown only inside AI Studio. Hence small batches, pauses and resumable runs. Batch size 20 and a 10-second pause are cautious guesses, not documented limits.
- **The maximum number of texts per batch** is not stated.
- **The REST response for `batchEmbedContents` is not shown**, and the reference and code samples differ on singular or plural. The adapter expects `embeddings[].values` and refuses anything else. The real run (§7) returned that shape.
- **Shutdown dates** were not found. Google's separate deprecations page was not read.

## 6. Limits

- Google's page indicates inputs over 8,192 tokens are truncated without an error. The longest passages seen are about 2,800 characters, far below this, but the job does not check it.
- New uploads are not embedded automatically. Run `scripts/embed_passages.py` after uploading; missing embeddings are reported by `--check`.
- On the free tier, Google may use submitted content to improve its products and human reviewers may read it. Use it only with open-access papers (`NFR-PRI-001`). Paid use is not used for product improvement, per Google's terms.

## 7. Real run

Manual real-model run, 2026-11-09, at commit b728134, with the developer's approval to send all stored passages (CC BY) to Google's free tier.

| Measure | Result |
|---|---|
| Passages embedded | 324 of 324, in one run with no rate-limit stop |
| Time | 3 minutes 21 seconds, mostly the pauses between 17 batches |
| Stored | 324 rows, one per passage, 768 dimensions, 324 distinct vectors |
| Vector length | 1.0000 for every vector, confirming Google's normalisation |
| Passage table | Unchanged: same 324 rows and fingerprint before and after |
| Run again | 0 sent, 0 missing |
| Cost | $0, free tier |

This shows embeddings were produced and stored. It does not show whether they improve retrieval; R4 measures that.
