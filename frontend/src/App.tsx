// Two views: upload, and one document (status, then structure). The open
// document is kept in the address bar.

import { useState } from "react";

import type { UploadResponse } from "./api/types";
import { DocumentView } from "./components/DocumentView";
import { Icon } from "./components/Icon";
import { UploadForm } from "./components/UploadForm";
import { useDocumentRoute } from "./lib/useDocumentRoute";

// How often a pending or processing document's status is checked.
const POLL_INTERVAL_MS = 1500;

export default function App({ pollIntervalMs = POLL_INTERVAL_MS }: { pollIntervalMs?: number }) {
  const [documentId, navigate] = useDocumentRoute();
  const [notice, setNotice] = useState<string | null>(null);

  function uploaded(upload: UploadResponse): void {
    setNotice(
      upload.created
        ? null
        : "This file was uploaded before, so it was not processed again. Showing the existing document.",
    );
    navigate(upload.document_id);
  }

  function goHome(): void {
    setNotice(null);
    navigate(null);
  }

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="masthead">
        <a
          className="wordmark"
          href="/"
          onClick={(event) => {
            event.preventDefault();
            goHome();
          }}
        >
          PaperPilot
        </a>
        <span className="masthead-note">Upload a paper and inspect what the parser stored</span>
      </header>

      <main id="main" className="page">
        {documentId === null ? (
          <UploadForm onUploaded={uploaded} />
        ) : (
          <>
            <a
              className="back-link"
              href="/"
              onClick={(event) => {
                event.preventDefault();
                goHome();
              }}
            >
              <Icon name="back" />
              Upload another PDF
            </a>
            {notice && (
              <p className="panel notice notice-info" role="status">
                <Icon name="info" />
                {notice}
              </p>
            )}
            <DocumentView
              key={documentId}
              documentId={documentId}
              pollIntervalMs={pollIntervalMs}
              onHome={goHome}
            />
          </>
        )}
      </main>
    </>
  );
}
