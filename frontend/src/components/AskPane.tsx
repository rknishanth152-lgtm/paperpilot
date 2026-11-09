// Ask about one paper (FR-UI-003). Shows what the API returns; validity, pages and
// sections are never derived here. No wording may claim that a source proves a
// claim: that is not evaluated (FR-CIT-005, AD-008).

import { ChevronRight, Info, LoaderCircle, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import {
  Button,
  Disclosure,
  DisclosurePanel,
  Heading,
  Tooltip,
  TooltipTrigger,
} from "react-aria-components";

import { ApiError, askQuestion } from "../api/client";
import type { AnswerResponse, CitationResponse, StatementResponse } from "../api/types";
import { formatPages } from "../lib/format";
import { CITATION_FAILURE_TEXT, partsText, searchMethodText } from "../lib/wording";

export type OnCite = (passageId: string, quote: string | null) => void;

interface Turn {
  id: number;
  question: string;
  answer: AnswerResponse | null;
  problem: string | null;
}

function numbering(answer: AnswerResponse): Map<string, number> {
  const numbers = new Map<string, number>();
  for (const statement of answer.statements) {
    for (const citation of statement.citations) {
      if (citation.valid && citation.passage_id && !numbers.has(citation.passage_id)) {
        numbers.set(citation.passage_id, numbers.size + 1);
      }
    }
  }
  return numbers;
}

function Citation({
  citation,
  numbers,
  onCite,
}: {
  citation: CitationResponse;
  numbers: Map<string, number>;
  onCite: OnCite;
}) {
  const passageId = citation.passage_id;
  if (!citation.valid || passageId === null) {
    return (
      <span className="cite cite-bad">
        {citation.reason ? CITATION_FAILURE_TEXT[citation.reason] : "Source not confirmed"}
      </span>
    );
  }
  const number = numbers.get(passageId) ?? 0;
  return (
    <TooltipTrigger delay={250} closeDelay={80}>
      <Button
        className="cite"
        aria-label={`Open source ${number} in the paper`}
        onPress={() => onCite(passageId, citation.quote)}
      >
        {number}
      </Button>
      {citation.quote && <Tooltip className="preview">“{citation.quote}”</Tooltip>}
    </TooltipTrigger>
  );
}

function Claim({
  statement,
  numbers,
  onCite,
}: {
  statement: StatementResponse;
  numbers: Map<string, number>;
  onCite: OnCite;
}) {
  return (
    <p className="claim">
      {statement.text}{" "}
      {statement.citations.map((citation, index) => (
        <Citation key={`${citation.alias}-${index}`} citation={citation} numbers={numbers} onCite={onCite} />
      ))}
      {statement.citations.length === 0 && <span className="cite cite-bad">No source given</span>}
    </p>
  );
}

function Verdict({ answer }: { answer: AnswerResponse }) {
  if (answer.validation_status === "failed") {
    return (
      <p className="verdict verdict-warn">
        <TriangleAlert className="icon" size={16} />
        <span>
          Some sources couldn't be confirmed in this paper. Check the paper before relying on
          this answer.
        </span>
      </p>
    );
  }
  if (answer.evidence_sufficiency === "insufficient") {
    return (
      <p className="verdict verdict-none">
        <Info className="icon" size={16} />
        <span>Not enough evidence in the parts of this paper that were read.</span>
      </p>
    );
  }
  return (
    <>
      {answer.evidence_sufficiency === "partial" && (
        <p className="verdict">
          <Info className="icon" size={16} />
          <span>This answers only part of your question.</span>
        </p>
      )}
      <p className="verdict">
        <span>
          Every quote above was found in this paper. Whether a source fully proves a claim is
          for you to judge.
        </span>
      </p>
    </>
  );
}

function Sources({
  answer,
  numbers,
  onCite,
}: {
  answer: AnswerResponse;
  numbers: Map<string, number>;
  onCite: OnCite;
}) {
  if (answer.evidence.length === 0) return null;
  const quotes = new Map<string, string | null>();
  for (const statement of answer.statements) {
    for (const citation of statement.citations) {
      if (citation.passage_id && !quotes.has(citation.passage_id)) {
        quotes.set(citation.passage_id, citation.quote);
      }
    }
  }
  return (
    <ul className="sources">
      {answer.evidence.map((item) => (
        <li key={item.passage_id}>
          <button
            type="button"
            className="source"
            onClick={() => onCite(item.passage_id, quotes.get(item.passage_id) ?? null)}
          >
            <b>{numbers.get(item.passage_id)}</b>
            <span>
              {item.section ?? "section unknown"}, {formatPages(item.page_start, item.page_end)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function HowMade({ answer }: { answer: AnswerResponse }) {
  const read = partsText(answer.retrieved_passage_ids.length);
  const dropped =
    answer.passages_dropped > 0
      ? ` ${partsText(answer.passages_dropped)} were left out for length.`
      : "";
  const made = answer.model
    ? `Read ${read} of this paper with ${answer.model}, using prompt ${answer.prompt_version ?? "unknown"}. They were chosen ${searchMethodText(answer.retrieval_method)}.${dropped}`
    : `No AI model was used. ${read} of this paper matched.`;
  return (
    <Disclosure className="disclosure">
      <Heading level={4}>
        <Button slot="trigger" className="disclosure-trigger">
          <ChevronRight className="icon" size={14} />
          How this answer was made
        </Button>
      </Heading>
      <DisclosurePanel>
        <p className="disclosure-body">
          {made} Whether a source supports a claim is not evaluated automatically.
        </p>
      </DisclosurePanel>
    </Disclosure>
  );
}

function Answer({ answer, onCite }: { answer: AnswerResponse; onCite: OnCite }) {
  const numbers = numbering(answer);
  return (
    <>
      {answer.statements.map((statement, index) => (
        <Claim key={index} statement={statement} numbers={numbers} onCite={onCite} />
      ))}
      <Verdict answer={answer} />
      {answer.limitations && <p className="limits">{answer.limitations}</p>}
      <Sources answer={answer} numbers={numbers} onCite={onCite} />
      <HowMade answer={answer} />
    </>
  );
}

export function AskPane({ documentId, onCite }: { documentId: string; onCite: OnCite }) {
  const [question, setQuestion] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [asking, setAsking] = useState(false);
  const nextId = useRef(1);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (turns.length > 0) end.current?.scrollIntoView({ block: "end" });
  }, [turns]);

  async function send(): Promise<void> {
    if (asking) return;
    const text = question.trim();
    if (!text) {
      setProblem("Type a question first.");
      return;
    }
    const id = nextId.current;
    nextId.current += 1;
    setProblem(null);
    setQuestion("");
    setAsking(true);
    setTurns((current) => [...current, { id, question: text, answer: null, problem: null }]);
    const finish = (change: Partial<Turn>): void =>
      setTurns((current) => current.map((turn) => (turn.id === id ? { ...turn, ...change } : turn)));
    try {
      finish({ answer: await askQuestion(documentId, text) });
    } catch (error) {
      finish({ problem: error instanceof ApiError ? error.message : "That question failed. Try again." });
    } finally {
      setAsking(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    void send();
  }

  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  }

  return (
    <>
      <div className="scroll thread">
        {turns.length === 0 && (
          <p className="intro">
            Ask anything about this paper. Answers come only from its text, and each one links
            to the sentence it came from.
          </p>
        )}
        {turns.map((turn) => (
          <article className="turn" key={turn.id}>
            <h3 className="question">{turn.question}</h3>
            {turn.answer && <Answer answer={turn.answer} onCite={onCite} />}
            {turn.problem && (
              <p className="alert" role="alert">
                <TriangleAlert className="icon" size={16} />
                {turn.problem}
              </p>
            )}
            {!turn.answer && !turn.problem && (
              <p className="waiting" role="status">
                <LoaderCircle className="icon spin" size={16} />
                Reading this paper and asking the AI model…
              </p>
            )}
          </article>
        ))}
        <div ref={end} />
      </div>
      <form className="composer" onSubmit={submit} noValidate>
        {problem && (
          <p className="alert small add-message" role="alert">
            <TriangleAlert className="icon" size={16} />
            {problem}
          </p>
        )}
        <div className="composer-box">
          <textarea
            className="composer-input"
            rows={1}
            aria-label="Ask about this paper"
            placeholder="Ask about this paper"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={keyDown}
          />
          <button type="submit" className="button" aria-busy={asking}>
            Ask
          </button>
        </div>
        <p className="muted small composer-hint">
          Your question and the matching parts of this paper are sent to the AI provider.
        </p>
      </form>
    </>
  );
}
