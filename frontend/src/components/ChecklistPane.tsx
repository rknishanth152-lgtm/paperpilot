// The reporting checklist for one paper (FR-REP-002, FR-REP-004).
// Status words come from the server, so no client can word "not found" as a
// finding about the paper. There is deliberately no total, score or summary
// count, and no red or green: nothing here may read as a grade.

import {
  Check,
  ChevronRight,
  Contrast,
  Info,
  LoaderCircle,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Button, Disclosure, DisclosurePanel, Heading } from "react-aria-components";

import { ApiError, getAssessment, runAssessment } from "../api/client";
import type {
  AssessmentEvidence,
  AssessmentItem,
  AssessmentResponse,
  ReportingStatus,
} from "../api/types";
import { formatPages } from "../lib/format";
import { partsText, searchMethodText } from "../lib/wording";
import type { OnCite } from "./AskPane";

const STATUS_ICON: Record<ReportingStatus, LucideIcon> = {
  reported: Check,
  partially_reported: Contrast,
  not_found: Info,
  needs_review: TriangleAlert,
};

function asMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "The checklist failed. Try again.";
}

function Evidence({
  evidence,
  title,
  onCite,
}: {
  evidence: AssessmentEvidence;
  title: string;
  onCite: OnCite;
}) {
  return (
    <li className="check-evidence">
      <p className="check-quote">
        <mark>{evidence.quote}</mark>
      </p>
      <p className="muted small check-where">
        <span>
          {evidence.section ?? "section unknown"}, {formatPages(evidence.page_start, evidence.page_end)}
        </span>
        <button
          type="button"
          className="link-button"
          aria-label={`Show the ${title} quote in the paper`}
          onClick={() => onCite(evidence.passage_id, evidence.quote)}
        >
          Show in the paper
        </button>
      </p>
    </li>
  );
}

function Item({ item, onCite }: { item: AssessmentItem; onCite: OnCite }) {
  const StatusIcon = STATUS_ICON[item.status];
  return (
    <li className="check-item">
      <div className="check-heading">
        <h3 className="check-title">{item.title}</h3>
        <span className={`status status-${item.status}`}>
          <StatusIcon className="icon" size={14} />
          {item.status_label}
        </span>
      </div>
      <p className="muted small check-question">{item.question}</p>
      <p className="check-text">{item.status_description}</p>
      {item.explanation && <p className="check-text">{item.explanation}</p>}
      {item.evidence.length > 0 && (
        <ul>
          {item.evidence.map((evidence) => (
            <Evidence
              key={evidence.passage_id}
              evidence={evidence}
              title={item.title}
              onCite={onCite}
            />
          ))}
        </ul>
      )}
      <p className="muted small check-count">Checked {partsText(item.passages_examined)} of the paper</p>
    </li>
  );
}

function Result({ assessment, onCite }: { assessment: AssessmentResponse; onCite: OnCite }) {
  const made = assessment.model
    ? `Used ${assessment.model} with prompt ${assessment.prompt_version ?? "unknown"}. Parts of the paper were chosen ${searchMethodText(assessment.retrieval_method)}.`
    : "No AI model was used.";
  return (
    <div className="checklist-result">
      <ol>
        {assessment.items.map((item) => (
          <Item key={item.key} item={item} onCite={onCite} />
        ))}
      </ol>
      <Disclosure className="disclosure">
        <Heading level={4}>
          <Button slot="trigger" className="disclosure-trigger">
            <ChevronRight className="icon" size={14} />
            How this was checked
          </Button>
        </Heading>
        <DisclosurePanel>
          <p className="disclosure-body">
            {assessment.checklist_version}. {made} Run on{" "}
            {new Date(assessment.created_at).toLocaleString()}. Earlier runs are kept.
          </p>
        </DisclosurePanel>
      </Disclosure>
    </div>
  );
}

export function ChecklistPane({ documentId, onCite }: { documentId: string; onCite: OnCite }) {
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

  return (
    <div className="scroll thread">
      <p className="check-text">
        Checks what this paper states about six reporting items. It is not a score or a
        judgement of the work.
      </p>
      <p className="muted small">
        Each item uses parts of this paper, which are sent to the configured AI provider.
      </p>
      {problem && (
        <p className="alert add-message" role="alert">
          <TriangleAlert className="icon" size={16} />
          {problem}
        </p>
      )}
      {!loading && (
        <p className="checklist-actions">
          <button type="button" className="button" aria-busy={running} onClick={() => void run()}>
            {running ? "Checking…" : assessment ? "Run again" : "Run checklist"}
          </button>
        </p>
      )}
      {running && (
        <p className="waiting" role="status">
          <LoaderCircle className="icon spin" size={16} />
          Checking each item against this paper. This can take a minute.
        </p>
      )}
      {assessment && <Result key={assessment.assessment_id} assessment={assessment} onCite={onCite} />}
    </div>
  );
}
