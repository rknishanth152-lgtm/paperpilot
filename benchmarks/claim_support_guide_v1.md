# Claim-support labelling guide, version 1

For `FR-EVL-004` (P6-T3). Fixed before any label was given. A change to this file makes a new version, and labels made under the old one are not mixed with labels made under the new one.

Each item shows a question, one statement from an answer, and the passage or passages it cites. Give **two separate labels**. Judge them one at a time, and do not let one change the other.

## Label 1: does the cited evidence support the statement?

This is the claim-support label from the PRD. Use only the passage text shown. Do not use what you know about the paper or the field, and do not judge whether the statement is true in the world.

| Label | Use when |
|---|---|
| `supported` | The passage states the whole statement or directly implies it. Paraphrase is fine. Numbers and direction match. |
| `partly_supported` | Part of the statement is supported and part is not, or the statement drops a qualifier in a way that changes its meaning, such as widening its scope. |
| `not_supported` | The passage does not say this, contradicts it, or is about something else. |
| `cannot_judge` | The passage is too garbled to read, or the statement depends on a table, figure or term you cannot resolve from what is shown. Not for items that are merely hard. |

If a statement cites several passages, judge them together.

## Label 2: does the statement answer the question?

An addition to `FR-EVL-004`, approved by the developer on 2026-11-09. A statement can be fully supported and still not address what was asked. Judge the one statement shown, and ignore whether it is supported.

| Label | Use when |
|---|---|
| `yes` | It gives what the question asks for. |
| `partly` | It is on the question but narrower, or gives a related measure instead of the one asked for. |
| `no` | It is about something else, even if it is true. |
| `cannot_judge` | You cannot tell what the question is asking. |

## Made-up examples

Question: "How fast did the glaciers retreat?"

| Statement | Passage | Label 1 | Label 2 |
|---|---|---|---|
| Glaciers retreated by 12 metres a year. | "Annual retreat averaged 12 m." | `supported` | `yes` |
| Glaciers retreated by 12 metres a year in every region. | "Annual retreat averaged 12 m in the Alps." | `partly_supported` | `yes` |
| Glaciers retreated by 20 metres a year. | "Annual retreat averaged 12 m." | `not_supported` | `yes` |
| Most of the glaciers studied were in the Alps. | "Most glaciers studied were in the Alps." | `supported` | `no` |

## How the numbers are computed

- Claim-support rate = `supported` ÷ all labelled statements, as defined in the PRD. `cannot_judge` stays in the denominator. `partly_supported` does not count as supported.
- Label 2 is reported on its own and is never combined into the claim-support rate.
- Both are reported with the sample size and the labeller's name.

## Rules

- Give your first considered judgement, and do not revise labels to reach a number.
- Once the report has been saved, any changed label is logged in `progress.md` with a reason.
- One person's labels show agreement with that person, not scientific truth.
