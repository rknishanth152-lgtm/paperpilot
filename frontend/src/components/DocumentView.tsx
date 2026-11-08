// One document: its real processing status, polled while it is pending or
// processing (AD-010), then either the failure with a Retry action or the
// parsed structure. Nothing here invents progress or status.

import { useEffect, useState } from "react";

import { ApiError, getDocument, getStructure, retryDocument } from "../api/client";
import type { DocumentResponse, StructureResponse } from "../api/types";
import { formatBytes } from "../lib/format";
import { Icon } from "./Icon";
import { QuestionPanel } from "./QuestionPanel";
import { StatusBadge } from "./StatusBadge";
import { StructureView } from "./StructureView";

const WAITING_TEXT = {
  pending: "Waiting for processing to start. This page updates by itself.",
  processing: "GROBID is parsing the PDF. This page updates by itself.",
} as const;

function asApiError(error: unknown): ApiError {
  return error instanceof ApiError
    ? error
    : new ApiError(null, "unexpected_error", "Something went wrong in this page. Try again.");
}

// Errors worth retrying from here: the server was unreachable or failed.
function canTryAgain(error: ApiError): boolean {
  return error.status === null || error.status >= 500;
}

interface Props {
  documentId: string;
  pollIntervalMs: number;
  onHome: () => void;
}

export function DocumentView({ documentId, pollIntervalMs, onHome }: Props) {
  const [document, setDocument] = useState<DocumentResponse | null>(null);
  const [structure, setStructure] = useState<StructureResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [retryError, setRetryError] = useState<ApiError | null>(null);
  const [retrying, setRetrying] = useState(false);
  // Changing this restarts the status check (after Try again or Retry).
  const [round, setRound] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function check(): Promise<void> {
      try {
        const next = await getDocument(documentId);
        if (cancelled) return;
        setDocument(next);
        if (next.status === "pending" || next.status === "processing") {
          timer = setTimeout(() => void check(), pollIntervalMs);
        } else if (next.status === "parsed") {
          const parsed = await getStructure(documentId);
          if (!cancelled) setStructure(parsed);
        }
      } catch (caught) {
        if (!cancelled) setError(asApiError(caught));
      }
    }

    void check();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [documentId, pollIntervalMs, round]);

  function restart(): void {
    setError(null);
    setDocument(null);
    setStructure(null);
    setRound((value) => value + 1);
  }

  async function retry(): Promise<void> {
    if (retrying) return;
    setRetrying(true);
    setRetryError(null);
    try {
      await retryDocument(documentId);
      restart();
    } catch (caught) {
      setRetryError(asApiError(caught));
    } finally {
      setRetrying(false);
    }
  }

  if (error) {
    return (
      <div className="panel notice notice-error" role="alert">
        <p className="notice-text">
          <Icon name="alert" />
          {error.message}
        </p>
        <div className="actions">
          {canTryAgain(error) && (
            <button type="button" className="button button-primary" onClick={restart}>
              Try again
            </button>
          )}
          <a
            href="/"
            className="button"
            onClick={(event) => {
              event.preventDefault();
              onHome();
            }}
          >
            Upload a PDF
          </a>
        </div>
      </div>
    );
  }

  if (document === null) {
    return (
      <p className="panel muted" role="status">
        Checking the document status…
      </p>
    );
  }

  return (
    <div className="document">
      <header className="panel document-header">
        <div className="document-heading">
          <h1 className="document-name">
            {document.original_filename ?? "Uploaded PDF (no file name)"}
          </h1>
          <StatusBadge status={document.status} />
        </div>
        <p className="muted document-facts">
          {formatBytes(document.size_bytes)} · SHA-256{" "}
          <code title={document.sha256}>{document.sha256.slice(0, 12)}…</code>
        </p>

        <div role="status" aria-live="polite">
          {(document.status === "pending" || document.status === "processing") && (
            <p className="waiting">{WAITING_TEXT[document.status]}</p>
          )}
        </div>

        {document.status === "failed" && (
          <div className="failure">
            <p className="failure-text">
              {document.failure_explanation ?? "Processing failed. No reason was recorded."}
            </p>
            {document.failure_reason && (
              <p className="muted failure-code">
                Reason code <code>{document.failure_reason}</code>
              </p>
            )}
            {retryError && (
              <p className="form-error" role="alert">
                <Icon name="alert" />
                {retryError.message}
              </p>
            )}
            <div className="actions">
              <button
                type="button"
                className="button button-primary"
                onClick={() => void retry()}
                aria-busy={retrying}
              >
                {retrying ? "Retrying…" : "Retry"}
              </button>
            </div>
          </div>
        )}
      </header>

      {document.status === "parsed" &&
        (structure ? (
          <>
            <QuestionPanel documentId={documentId} />
            <StructureView structure={structure} />
          </>
        ) : (
          <p className="panel muted" role="status">
            Loading the parsed structure…
          </p>
        ))}
    </div>
  );
}
