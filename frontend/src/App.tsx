// The reading desk: your library, the conversation about one paper, and the paper
// itself. The open paper is kept in the address bar.

import { BookOpen, Library as LibraryIcon, LoaderCircle, MessageSquare, TriangleAlert } from "lucide-react";
import { useCallback, useRef, useState, type ReactNode } from "react";
import { Tab, TabList, TabPanel, Tabs } from "react-aria-components";
import { Group, Panel, Separator } from "react-resizable-panels";

import { ApiError, retryDocument } from "./api/client";
import type { LibraryDocument, UploadResponse } from "./api/types";
import { AddPaper } from "./components/AddPaper";
import { AskPane } from "./components/AskPane";
import { ChecklistPane } from "./components/ChecklistPane";
import { Library } from "./components/Library";
import { LogoMark } from "./components/Logo";
import { PaperPane, type PaperFocus } from "./components/PaperPane";
import { useDocumentRoute } from "./lib/useDocumentRoute";
import { useIsWide } from "./lib/useIsWide";
import { useLibrary } from "./lib/useLibrary";
import { STATUS_TEXT } from "./lib/wording";

const POLL_INTERVAL_MS = 1500;

type Area = "library" | "work" | "paper";

function Home({ onAdded }: { onAdded: (upload: UploadResponse) => void }) {
  return (
    <div className="home">
      <h2 className="home-title">Start with a paper</h2>
      <p className="home-text">
        Add a PDF, ask questions in your own words, and see the exact sentence behind every
        answer.
      </p>
      <AddPaper onAdded={onAdded} large />
      <p className="muted small privacy">
        Your PDF stays on this computer. Only your questions and the parts of a paper needed to
        answer them go to the AI provider.
      </p>
    </div>
  );
}

function Conversation({
  document,
  onCite,
}: {
  document: LibraryDocument;
  onCite: (passageId: string, quote: string | null) => void;
}) {
  if (document.status !== "parsed") {
    return (
      <div className="thread">
        <p className="intro">You can ask questions once this paper is ready.</p>
      </div>
    );
  }
  return (
    <Tabs className="tabs">
      <TabList className="tab-list" aria-label="Work with this paper">
        <Tab id="ask" className="tab">
          Ask
        </Tab>
        <Tab id="checklist" className="tab">
          Reporting checklist
        </Tab>
      </TabList>
      <TabPanel id="ask" className="tab-panel" shouldForceMount>
        <AskPane documentId={document.document_id} onCite={onCite} />
      </TabPanel>
      <TabPanel id="checklist" className="tab-panel" shouldForceMount>
        <ChecklistPane documentId={document.document_id} onCite={onCite} />
      </TabPanel>
    </Tabs>
  );
}

function PaperArea({
  document,
  focus,
  onRetry,
  retryProblem,
}: {
  document: LibraryDocument;
  focus: PaperFocus | null;
  onRetry: () => void;
  retryProblem: string | null;
}) {
  if (document.status === "parsed") {
    return <PaperPane documentId={document.document_id} focus={focus} />;
  }
  if (document.status === "failed") {
    return (
      <div className="placeholder">
        <h2 className="paper-title">{STATUS_TEXT.failed}</h2>
        <p>{document.failure_explanation ?? "No reason was recorded."}</p>
        {retryProblem && (
          <p className="alert small" role="alert">
            <TriangleAlert className="icon" size={16} />
            {retryProblem}
          </p>
        )}
        <button type="button" className="button" onClick={onRetry}>
          Try again
        </button>
      </div>
    );
  }
  return (
    <p className="waiting" role="status" aria-live="polite">
      <LoaderCircle className="icon spin" size={16} />
      {STATUS_TEXT[document.status]}
    </p>
  );
}

function NotInLibrary() {
  return <p className="intro">This paper isn't in your library.</p>;
}

export default function App({ pollIntervalMs = POLL_INTERVAL_MS }: { pollIntervalMs?: number }) {
  const [documentId, navigate] = useDocumentRoute();
  const { documents, problem, refresh } = useLibrary(pollIntervalMs);
  const wide = useIsWide();
  const [notice, setNotice] = useState<string | null>(null);
  const [retryProblem, setRetryProblem] = useState<string | null>(null);
  const [focus, setFocus] = useState<PaperFocus | null>(null);
  const [area, setArea] = useState<Area>("library");
  const tick = useRef(0);

  const open = useCallback(
    (id: string) => {
      setNotice(null);
      setFocus(null);
      setRetryProblem(null);
      navigate(id);
      setArea("work");
    },
    [navigate],
  );

  const added = useCallback(
    (upload: UploadResponse) => {
      open(upload.document_id);
      setNotice(upload.created ? null : "This paper is already in your library.");
      void refresh();
    },
    [open, refresh],
  );

  const cite = useCallback((passageId: string, quote: string | null) => {
    tick.current += 1;
    setFocus({ passageId, quote, tick: tick.current });
    setArea("paper");
  }, []);

  async function retry(): Promise<void> {
    if (documentId === null) return;
    setRetryProblem(null);
    try {
      await retryDocument(documentId);
      await refresh();
    } catch (error) {
      setRetryProblem(error instanceof ApiError ? error.message : "That didn't work. Try again.");
    }
  }

  const selected = documents?.find((document) => document.document_id === documentId) ?? null;
  const missing = documentId !== null && documents !== null && selected === null;

  const library = (
    <Library
      documents={documents}
      problem={problem}
      selectedId={documentId}
      notice={notice}
      onSelect={open}
      onAdded={added}
      onRetry={() => void refresh()}
    />
  );

  let work: ReactNode = null;
  let paper: ReactNode = null;
  if (documentId === null) {
    work = <Home onAdded={added} />;
  } else if (missing) {
    work = (
      <div className="thread">
        <NotInLibrary />
      </div>
    );
  } else if (selected) {
    work = <Conversation key={selected.document_id} document={selected} onCite={cite} />;
    paper = (
      <PaperArea
        key={selected.document_id}
        document={selected}
        focus={focus}
        onRetry={() => void retry()}
        retryProblem={retryProblem}
      />
    );
  }

  // The skip link's target. On a narrow screen the whole visible area is the
  // main region, so it exists whichever area is showing.
  const paperPane = (
    <section className="sheet" aria-label="The paper" tabIndex={0}>
      {paper}
    </section>
  );

  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <h1 className="logo">
          <LogoMark />
          PaperPilot
        </h1>
        <span className="tagline">Read research with every answer traced to its source</span>
      </header>

      {wide ? (
        <Group key={paper ? "three" : "two"} orientation="horizontal" className="desk">
          <Panel defaultSize="21%" minSize="15%">
            {library}
          </Panel>
          <Separator className="gutter" aria-label="Resize the library" />
          <Panel defaultSize={paper ? "37%" : "79%"} minSize="26%">
            <main id="main" className="pane work">
              {work}
            </main>
          </Panel>
          {paper && <Separator className="gutter" aria-label="Resize the paper" />}
          {paper && (
            <Panel defaultSize="42%" minSize="26%">
              <div className="pane">{paperPane}</div>
            </Panel>
          )}
        </Group>
      ) : (
        <div className="narrow">
          <main id="main" className="narrow-area">
            {area === "library" && library}
            {area === "work" && <div className="pane work">{work}</div>}
            {area === "paper" && <div className="pane">{paperPane}</div>}
          </main>
          <nav className="bottom-nav" aria-label="Sections">
            <button
              type="button"
              className="bottom-tab"
              aria-current={area === "library" ? "page" : undefined}
              onClick={() => setArea("library")}
            >
              <LibraryIcon className="icon" size={20} />
              Library
            </button>
            <button
              type="button"
              className="bottom-tab"
              aria-current={area === "work" ? "page" : undefined}
              onClick={() => setArea("work")}
            >
              <MessageSquare className="icon" size={20} />
              Ask
            </button>
            <button
              type="button"
              className="bottom-tab"
              aria-current={area === "paper" ? "page" : undefined}
              onClick={() => setArea("paper")}
              disabled={paper === null}
            >
              <BookOpen className="icon" size={20} />
              Paper
            </button>
          </nav>
        </div>
      )}
    </div>
  );
}
