// The paper itself: stored text exactly as stored, in order. A citation scrolls
// here and draws the highlighter over the exact sentence. Pages and sections come
// from the database; an unknown page says so (DR-007).

import { TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ApiError, getStructure } from "../api/client";
import type { Passage, StructureResponse } from "../api/types";
import { formatPages, groupPassages } from "../lib/format";
import { locateQuote } from "../lib/quote";

export interface PaperFocus {
  passageId: string;
  quote: string | null;
  tick: number; // changes on every click, so the same citation can replay
}

function Paragraph({ text, quote }: { text: string; quote: string | null | undefined }) {
  if (quote === undefined) return <p className="para">{text}</p>;
  const span = quote === null ? null : locateQuote(text, quote);
  if (span === null) {
    return (
      <p className="para">
        <mark>{text}</mark>
      </p>
    );
  }
  return (
    <p className="para">
      {text.slice(0, span[0])}
      <mark>{text.slice(span[0], span[1])}</mark>
      {text.slice(span[1])}
    </p>
  );
}

function Para({ passage, focus }: { passage: Passage; focus: PaperFocus | null }) {
  const selected = focus?.passageId === passage.passage_id;
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!selected) return;
    const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    ref.current?.scrollIntoView({ block: "center", behavior: reduced ? "auto" : "smooth" });
  }, [selected, focus?.tick]);

  return (
    <div ref={ref} key={selected ? focus?.tick : "still"}>
      <Paragraph text={passage.text} quote={selected ? focus?.quote : undefined} />
      <p className={passage.page_start === null ? "para-page para-page-unknown" : "para-page"}>
        {formatPages(passage.page_start, passage.page_end)}
      </p>
    </div>
  );
}

export function PaperPane({ documentId, focus }: { documentId: string; focus: PaperFocus | null }) {
  const [structure, setStructure] = useState<StructureResponse | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getStructure(documentId)
      .then((found) => {
        if (!cancelled) setStructure(found);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setProblem(error instanceof ApiError ? error.message : "This paper couldn't be opened.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  if (problem) {
    return (
      <p className="alert" role="alert">
        <TriangleAlert className="icon" size={16} />
        {problem}
      </p>
    );
  }
  if (structure === null) {
    return (
      <p className="muted" role="status">
        Opening the paper…
      </p>
    );
  }

  const { paper, passages } = structure;
  return (
    <article>
      <h2 className="paper-title">{paper.title ?? "Untitled paper"}</h2>
      <p className="muted byline">
        {paper.authors.length > 0 ? paper.authors.join(", ") : "Authors unknown"}
      </p>
      {groupPassages(passages).map((group) => (
        <section key={group.key}>
          <h3 className="section-title">{group.label}</h3>
          {group.passages.map((passage) => (
            <Para key={passage.passage_id} passage={passage} focus={focus} />
          ))}
        </section>
      ))}
    </article>
  );
}
