// The papers you have added, newest first, with plain status words.

import { LoaderCircle, TriangleAlert } from "lucide-react";

import type { LibraryDocument, UploadResponse } from "../api/types";
import { STATUS_TEXT } from "../lib/wording";
import { AddPaper } from "./AddPaper";

interface Props {
  documents: LibraryDocument[] | null;
  problem: string | null;
  selectedId: string | null;
  notice: string | null;
  onSelect: (documentId: string) => void;
  onAdded: (upload: UploadResponse) => void;
  onRetry: () => void;
}

function displayName(document: LibraryDocument): string {
  return document.title ?? document.original_filename ?? "Untitled paper";
}

function Row({
  document,
  selected,
  onSelect,
}: {
  document: LibraryDocument;
  selected: boolean;
  onSelect: () => void;
}) {
  const busy = document.status === "pending" || document.status === "processing";
  return (
    <li>
      <button type="button" className="paper-row" aria-current={selected || undefined} onClick={onSelect}>
        <span className="paper-row-title">{displayName(document)}</span>
        <span className="paper-row-status">
          {busy && <LoaderCircle className="icon spin" size={13} />}
          {document.status === "failed" && <TriangleAlert className="icon" size={13} />}
          <span>{STATUS_TEXT[document.status]}</span>
        </span>
      </button>
    </li>
  );
}

export function Library({ documents, problem, selectedId, notice, onSelect, onAdded, onRetry }: Props) {
  return (
    <nav className="pane library" aria-label="Your library">
      <AddPaper onAdded={onAdded} />
      {notice && (
        <p className="notice add-message" role="status">
          {notice}
        </p>
      )}
      <h2 className="library-title">Your library</h2>
      <div className="scroll">
        {problem && documents === null && (
          <div className="empty-library">
            <p className="alert small" role="alert">
              <TriangleAlert className="icon" size={16} />
              {problem}
            </p>
            <button type="button" className="button button-quiet add-message" onClick={onRetry}>
              Try again
            </button>
          </div>
        )}
        {documents === null && !problem && <p className="muted empty-library">Opening your library…</p>}
        {documents?.length === 0 && (
          <p className="muted empty-library">Your library is empty. Add a paper to begin.</p>
        )}
        {documents && documents.length > 0 && (
          <ul>
            {documents.map((document) => (
              <Row
                key={document.document_id}
                document={document}
                selected={document.document_id === selectedId}
                onSelect={() => onSelect(document.document_id)}
              />
            ))}
          </ul>
        )}
      </div>
    </nav>
  );
}
