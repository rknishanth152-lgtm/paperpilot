# Reproducibility checklist baseline

| Field | Value |
|---|---|
| Task | R8 (P11-T7; `FR-EVL-006`, `FR-REP-005`) |
| Date | 2026-11-09 |
| Kind | **Manual real-model run** |
| Labels | `benchmarks/reproducibility_labels_v1.json`, 18 labels by one labeller, given before any model assessed these papers |
| Papers | p1, p4 and p5 |

## 1. Method fixed before any result

Written and committed before any model assessed the labelled papers, and coded in `tests/evaluation/score_assessment.py`.

- **Agreement** is items where the assessed status equals the label, over all 18.
- **Commonest-label comparison.** The labels are 16 `reported` and 2 `not_found`, so always answering `reported` would agree on 16 of 18. The real score is reported beside that figure.
- **Per status:** recall (of items labelled this, how many were assessed this) and precision (of items assessed this, how many were labelled this). A status with no labels has no recall.
- **`not_found` versus `needs_review` confusion** is reported only as measurable if both labels occur. With no `needs_review` labels it is not measurable from this set.
- **Overstated and understated.** Among `reported`, `partially_reported` and `not_found`, whether the assessment claimed more or less than the label. `needs_review` claims nothing and is excluded.
- A brief provider outage retries that paper after a wait. It does not change what is scored. Two earlier attempts stopped on such an outage and saved no score.
- Two runs, because answers vary between runs. Neither the prompt nor the checklist is changed after seeing results unless that change is logged here.

## 2. Result

Two runs from clean commit 218c17f, `gemini-3.5-flash-lite`, prompt `reproducibility-v1`, semantic search, 8 parts of the paper per item. Result files: `reproducibility-score-20261109T171121Z-218c17f.json`, `reproducibility-score-20261109T171357Z-218c17f.json`. The statuses of all 18 items were the same in both runs.

| Measure | Result |
|---|---|
| Agreement with the labels | **15 of 18 (83%)** |
| Always answering `reported` would agree on | 16 of 18 (89%) |
| Overstated (claimed more than the label) | **0** |
| Understated (claimed less than the label) | 2 |
| Assessed `needs_review` where the label was `reported` | 1 |

**The assessment does not beat always answering `reported`.** That comparison is unforgiving on a set where 16 of 18 labels are the same, but the headline agreement figure should not be read as skill.

| Status | Labelled | Assessed | Agreed | Recall | Precision |
|---|---|---|---|---|---|
| `reported` | 16 | 13 | 13 | 81% | **100%** |
| `partially_reported` | 0 | 1 | 0 | not measurable | 0% |
| `not_found` | 2 | 3 | 2 | 100% | 67% |
| `needs_review` | 0 | 1 | 0 | not measurable | 0% |

The useful pattern is that the disagreements are all cautious. Every one of the 13 items assessed `reported` was also labelled `reported`, and the assessment never claimed more than the labeller did.

| Paper and item | Label | Assessed in both runs |
|---|---|---|
| p1, experiment or analysis procedure | `reported` | `needs_review` (model uncertain) |
| p1, software and computing environment | `reported` | `partially_reported` |
| p5, data access | `reported` | `not_found` |

## 3. Not established

- **`not_found` versus `needs_review` confusion is not measurable**, because no item was labelled `needs_review`. `FR-EVL-006` asks for this figure, and it is left open. The rule that a failed parse never gives `not_found` is covered by fault-injection tests instead.
- **Accuracy for `partially_reported` and `needs_review` is not measurable**, because neither was ever labelled.
- These are 18 items from 3 papers and one labeller, with one model. Agreement is with that person on PaperPilot's stored text, and says nothing about whether any paper can be reproduced (`RISK-15`).
- Identical statuses in two runs show consistency on this occasion, not correctness.
- The p5 data access miss was not investigated. Retrieval, the item's definition or the model could each be responsible, and changing any of them now would be tuning on this set.

Two earlier attempts stopped on a brief provider outage and saved no score, and two diagnostic assessments of p4 and p5 were run to find the cause. Their statuses were not looked at or scored.
