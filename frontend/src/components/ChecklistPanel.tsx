// The reporting checklist for one paper (FR-REP-002, FR-REP-004).
// Shows what the API returns. Status words come from the server, so no client can
// word "not found" as a finding about the paper. There is deliberately no total,
// score or summary count, and no red or green: nothing here may read as a grade.

import { useEffect, useId, useState } from "react";

import { ApiError, getAssessment, runAssessment } from "../api/client";
import type {
  AssessmentEvidence,
  AssessmentItem,
  AssessmentResponse,
  ReportingStatus,
} from "../api/types";
import { formatPages } from "../lib/format";
import { Icon, type IconName } from "./Icon";

const STATUS_ICON: Record<ReportingStatus, IconName> = {
  reported: "check",
  partially_reported: "half",
  not_found: "info",
  needs_review: "alert",
};

function asMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "The checklist failed. Try again.";
}

function Evidence({ evidence }: { evidence: AssessmentEvidence }) {
  return (
    <li className="checklist-evidence">
      <p className="checklist-quote">
        <mark>{evidence.quote}</mark>
      </p>
      <p className="muted checklist-where">
        <span className={evidence.section === null ? "unknown" : undefined}>
          {evidence.section ?? "section unknown"}
        </span>
        {" · "}
        <span className={evidence.page_start === null ? "unknown" : undefined}>
          {formatPages(evidence.page_start, evidence.page_end)}
        </span>
      </p>
      <details className="checklist-passage">
        <summary>Show the full passage</summary>
        <p className="passage-text">{evidence.text}</p>
      </details>
    </li>
  );
}

function Item({ item }: { item: AssessmentItem }) {
  const examined = `${item.passages_examined} ${
    item.passages_examined === 1 ? "passage" : "passages"
  } examined`;
  return (
    <li className="checklist-item">
      <div className="checklist-heading">
        <h3 className="checklist-title">{item.title}</h3>
        <span className={`badge checklist-badge badge-${item.status}`}>
          <Icon name={STATUS_ICON[item.status]} />
          {item.status_label}
        </span>
      </div>
      <p className="muted checklist-question">{item.question}</p>
      <p className="checklist-description">{item.status_description}</p>
      {item.explanation && <p className="checklist-explanation">{item.explanation}</p>}
      {item.evidence.length > 0 && (
        <ul className="checklist-evidence-list">
          {item.evidence.map((evidence) => (
            <Evidence key={evidence.passage_id} evidence={evidence} />
          ))}
        </ul>
      )}
      <p className="muted checklist-examined">{examined}</p>
    </li>
  );
}

function Result({ assessment }: { assessment: AssessmentResponse }) {
  const produced = assessment.model
    ? `Model ${assessment.model} · prompt ${assessment.prompt_version ?? "unknown"} · ${
        assessment.retrieval_method ?? "no retrieval"
      }`
    : "No AI model was used";
  return (
    <div className="checklist-result">
      <ol className="checklist-items">
        {assessment.items.map((item) => (
          <Item key={item.key} item={item} />
        ))}
      </ol>
      <p className="answer-details">
        {assessment.checklist_version} · {produced} ·{" "}
        {new Date(assessment.created_at).toLocaleString()}
      </p>
    </div>
  );
}

export function ChecklistPanel({ documentId }: { documentId: string }) {
  const titleId = useId();
  const [assessment, setAssessment] = useState<AssessmentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getAssessment(documentId)
      .then((found) => {
        if (!cancelled) setAssessment(found);
      })
      .catch((error: unknown) => {
        const nothingYet = error instanceof ApiError && error.code === "assessment_not_found";
        if (!cancelled && !nothingYet) setProblem(asMessage(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  async function run(): Promise<void> {
    if (running) return;
    setRunning(true);
    setProblem(null);
    try {
      setAssessment(await runAssessment(documentId));
    } catch (error) {
      setProblem(asMessage(error));
    } finally {
      setRunning(false);
    }
  }

  const idleLabel = assessment ? "Run again" : "Run checklist";

  return (
    <section className="panel checklist-panel" aria-labelledby={titleId}>
      <h2 className="question-title" id={titleId}>
        Reporting checklist
      </h2>
      <p className="checklist-intro">
        Checks what this paper states about six reporting items. It is not a score or a
        judgement of the work.
      </p>
      <p className="muted question-hint">
        Each item uses passages found in this paper. Those passages are sent to the
        configured AI provider.
      </p>
      {problem && (
        <p className="form-error" role="alert">
          <Icon name="alert" />
          {problem}
        </p>
      )}
      {!loading && (
        <div className="actions">
          <button
            type="button"
            className="button button-primary"
            aria-busy={running}
            onClick={() => void run()}
          >
            {running ? "Checking…" : idleLabel}
          </button>
        </div>
      )}
      {running && (
        <p className="waiting-answer" role="status">
          <Icon name="spinner" className="spin" />
          Checking each item against this paper. This can take a minute.
        </p>
      )}
      {assessment && <Result key={assessment.assessment_id} assessment={assessment} />}
    </section>
  );
}
