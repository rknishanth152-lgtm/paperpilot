// What the parser stored for a document (FR-ING-009, FR-UI-002): metadata, then
// every passage in order under its section, with its page or "page unknown".
// Passage text is shown exactly as stored.

import type { StructureResponse } from "../api/types";
import { formatPages, groupPassages } from "../lib/format";

function orMissing(value: string | null | undefined, missing: string): string {
  return value ? value : missing;
}

export function StructureView({ structure }: { structure: StructureResponse }) {
  const { paper, parser, passages } = structure;
  const groups = groupPassages(passages);

  return (
    <div className="structure">
      <section className="panel metadata" aria-labelledby="paper-title">
        <h2 id="paper-title" className={paper.title ? "paper-title" : "paper-title missing"}>
          {orMissing(paper.title, "No title found by the parser")}
        </h2>
        <dl className="facts">
          <div>
            <dt>Authors</dt>
            <dd>
              {paper.authors.length > 0
                ? paper.authors.join(", ")
                : "No authors found by the parser"}
            </dd>
          </div>
          <div>
            <dt>DOI</dt>
            <dd>{orMissing(paper.doi, "No DOI found by the parser")}</dd>
          </div>
          <div>
            <dt>Pages</dt>
            <dd>{structure.page_count ?? "unknown"}</dd>
          </div>
          <div>
            <dt>Passages</dt>
            <dd>{passages.length}</dd>
          </div>
          <div>
            <dt>Parser</dt>
            <dd>
              {parser.name} {parser.version}
            </dd>
          </div>
        </dl>
      </section>

      <div className="reader">
        {groups.length > 1 && (
          <nav className="toc" aria-label="Sections">
            <h2 className="toc-title">Sections</h2>
            <ol>
              {groups.map((group) => (
                <li key={group.key}>
                  <a href={`#section-${group.key}`}>{group.label}</a>
                </li>
              ))}
            </ol>
          </nav>
        )}

        <div className="passages">
          {groups.map((group) => (
            <section
              key={group.key}
              id={`section-${group.key}`}
              className="section"
              aria-labelledby={`heading-${group.key}`}
            >
              <h3 id={`heading-${group.key}`} className="section-title">
                {group.label}
              </h3>
              <ol className="passage-list">
                {group.passages.map((passage) => (
                  <li key={passage.passage_id} className="passage">
                    <p className="passage-text">{passage.text}</p>
                    <p className="passage-meta">
                      <span>Passage {passage.ordinal + 1}</span>
                      <span aria-hidden="true">·</span>
                      <span className={passage.page_start === null ? "unknown" : undefined}>
                        {formatPages(passage.page_start, passage.page_end)}
                      </span>
                    </p>
                  </li>
                ))}
              </ol>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
