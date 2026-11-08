// Ask a question about this paper and see the checked answer (FR-UI-003).
// Shows what the API returns; validity, pages and sections are never derived here.
// Validity is always stated in words, and no wording may claim that a passage
// supports a statement: that is not evaluated (FR-CIT-005).

import { useId, useState, type FormEvent } from "react";

import { ApiError, askQuestion } from "../api/client";
import type {
  AnswerResponse,
  CitationFailure,
  CitationResponse,
  EvidencePassage,
  StatementResponse,
} from "../api/types";
import { formatPages } from "../lib/format";
import { Icon } from "./Icon";

const FAILURE_LABEL: Record<CitationFailure, string> = {
  passage_not_found: "Not found",
  not_in_context: "Not shown to the model",
  wrong_paper: "Outside the selected paper",
  quote_mismatch: "Quote not in passage",
};

function Citation({ citation }: { citation: CitationResponse }) {
  if (citation.valid) {
    return (
      <a className="citation citation-valid" href={`#evidence-${citation.alias}`}>
        <Icon name="check" />
        {citation.alias} · Valid
      </a>
    );
  }
  const label = citation.reason ? FAILURE_LABEL[citation.reason] : "Invalid";
  return (
    <span className="citation citation-invalid">
      <Icon name="alert" />
      {citation.alias} · {label}
    </span>
  );
}

function Statement({ statement }: { statement: StatementResponse }) {
  const quotes = statement.citations.filter((citation) => citation.quote !== null);
  return (
    <li className={statement.has_valid_citation ? "statement" : "statement statement-unverified"}>
      <p className="statement-text">{statement.text}</p>
      <div className="citations">
        {statement.citations.map((citation, index) => (
          <Citation key={`${citation.alias}-${index}`} citation={citation} />
        ))}
        {statement.citations.length === 0 && (
          <span className="citation citation-invalid">
            <Icon name="alert" />
            No citation
          </span>
        )}
        {!statement.has_valid_citation && statement.citations.length > 0 && (
          <span className="citation citation-invalid">Not verified</span>
        )}
      </div>
      {quotes.map((citation, index) => (
        <p className="citation-quote" key={`${citation.alias}-quote-${index}`}>
          {citation.alias}: “{citation.quote}”
        </p>
      ))}
    </li>
  );
}

function Evidence({ item }: { item: EvidencePassage }) {
  return (
    <li className="evidence-item" id={`evidence-${item.alias}`}>
      <p className="evidence-meta">
        <span>{item.alias}</span>
        <span>{item.paper_title ?? "Untitled paper"}</span>
        <span className={item.section === null ? "unknown" : undefined}>
          {item.section ?? "section unknown"}
        </span>
        <span className={item.page_start === null ? "unknown" : undefined}>
          {formatPages(item.page_start, item.page_end)}
        </span>
      </p>
      <p className="passage-text">{item.text}</p>
    </li>
  );
}

function Status({ answer }: { answer: AnswerResponse }) {
  if (answer.validation_status === "failed") {
    return (
      <div className="answer-status answer-status-failed">
        <p className="answer-status-title">
          <Icon name="alert" />
          Citations failed checks
        </p>
        <p className="answer-status-note">
          At least one citation could not be verified. Do not treat this answer as
          evidence-backed.
        </p>
      </div>
    );
  }
  if (answer.evidence_sufficiency === "insufficient") {
    return (
      <div className="answer-status answer-status-insufficient">
        <p className="answer-status-title">
          <Icon name="info" />
          Not enough evidence
        </p>
        <p className="answer-status-note">
          The material searched does not answer this question.
        </p>
      </div>
    );
  }
  return (
    <div className="answer-status answer-status-validated">
      <p className="answer-status-title">
        <Icon name="check" />
        Citations checked
      </p>
      <p className="answer-status-note">
        Every citation points to a real passage, and any quote is in it. This does not
        confirm that the passages support the statements.
      </p>
      {answer.evidence_sufficiency === "partial" && (
        <p className="answer-status-note">This answer covers only part of the question.</p>
      )}
    </div>
  );
}

function Details({ answer }: { answer: AnswerResponse }) {
  const produced = answer.model
    ? `Model ${answer.model} · prompt ${answer.prompt_version ?? "unknown"}`
    : "No AI model was used";
  return (
    <p className="answer-details">
      {produced} · {answer.retrieval_method} · {answer.retrieved_passage_ids.length} passages
      retrieved, {answer.passages_dropped} dropped · Claim support: not evaluated
    </p>
  );
}

function Answer({ answer }: { answer: AnswerResponse }) {
  const headingId = useId();
  return (
    <div className="answer">
      <Status answer={answer} />
      {answer.statements.length > 0 && (
        <ol className="statements">
          {answer.statements.map((statement, index) => (
            <Statement key={index} statement={statement} />
          ))}
        </ol>
      )}
      {answer.limitations && (
        <>
          <h3 className="answer-heading">Limitations</h3>
          <p>{answer.limitations}</p>
        </>
      )}
      {answer.evidence.length > 0 && (
        <section aria-labelledby={headingId}>
          <h3 className="answer-heading" id={headingId}>
            {answer.validation_status === "failed"
              ? "Passages behind the valid citations only"
              : "Evidence"}
          </h3>
          <ol className="evidence-list">
            {answer.evidence.map((item) => (
              <Evidence key={item.passage_id} item={item} />
            ))}
          </ol>
        </section>
      )}
      <Details answer={answer} />
    </div>
  );
}

export function QuestionPanel({ documentId }: { documentId: string }) {
  const titleId = useId();
  const inputId = useId();
  const hintId = useId();
  const [question, setQuestion] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [answer, setAnswer] = useState<AnswerResponse | null>(null);
  const [asking, setAsking] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (asking) return;
    if (!question.trim()) {
      setProblem("Enter a question first.");
      return;
    }
    setAsking(true);
    setProblem(null);
    setAnswer(null);
    try {
      setAnswer(await askQuestion(documentId, question));
    } catch (error) {
      setProblem(error instanceof ApiError ? error.message : "The question failed. Try again.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <section className="panel question-panel" aria-labelledby={titleId}>
      <h2 className="question-title" id={titleId}>
        Ask about this paper
      </h2>
      <form className="question-form" onSubmit={(event) => void submit(event)} noValidate>
        <label className="question-label" htmlFor={inputId}>
          Your question
        </label>
        <textarea
          id={inputId}
          className="question-input"
          value={question}
          aria-describedby={hintId}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <p className="muted question-hint" id={hintId}>
          Answers use only passages found in this paper. Your question and those passages
          are sent to the configured AI provider.
        </p>
        {problem && (
          <p className="form-error" role="alert">
            <Icon name="alert" />
            {problem}
          </p>
        )}
        <div className="actions">
          <button type="submit" className="button button-primary" aria-busy={asking}>
            {asking ? "Asking…" : "Ask"}
          </button>
        </div>
      </form>
      {asking && (
        <p className="waiting-answer" role="status">
          <Icon name="spinner" className="spin" />
          Searching this paper and asking the AI model.
        </p>
      )}
      {answer && <Answer answer={answer} />}
    </section>
  );
}
