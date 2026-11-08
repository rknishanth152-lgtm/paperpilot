import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { DocumentResponse, StructureResponse } from "./api/types";

// --- A fake backend: queued responses per "METHOD path" -------------------

type Reply = { status: number; body: unknown } | "network_error";
let replies: Map<string, Reply[]>;
let calls: string[];

function on(method: string, path: string, ...queue: Reply[]): void {
  replies.set(`${method} ${path}`, queue);
}

function ok(body: unknown, status = 200): Reply {
  return { status, body };
}

beforeEach(() => {
  replies = new Map();
  calls = [];
  window.history.replaceState(null, "", "/");
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const key = `${init?.method ?? "GET"} ${url}`;
      calls.push(key);
      const queue = replies.get(key);
      if (!queue || queue.length === 0) throw new Error(`unexpected request: ${key}`);
      // The last reply repeats, so polling can keep asking.
      const reply = queue.length > 1 ? queue.shift()! : queue[0]!;
      if (reply === "network_error") throw new TypeError("Failed to fetch");
      return new Response(JSON.stringify(reply.body), { status: reply.status });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const ID = "0190a1b2-0000-7000-8000-000000000001";

function documentBody(overrides: Partial<DocumentResponse> = {}): DocumentResponse {
  return {
    document_id: ID,
    status: "pending",
    failure_reason: null,
    failure_explanation: null,
    original_filename: "paper.pdf",
    sha256: "a".repeat(64),
    size_bytes: 2048,
    created_at: "2026-11-04T10:00:00Z",
    updated_at: "2026-11-04T10:00:00Z",
    ...overrides,
  };
}

const STRUCTURE: StructureResponse = {
  document_id: ID,
  status: "parsed",
  parser: { name: "grobid", version: "0.9.1" },
  page_count: 2,
  paper: {
    paper_id: "p1",
    title: "A Synthetic Paper",
    authors: ["Ada B Example", "Ben Sample"],
    abstract: null,
    doi: null,
  },
  passages: [
    {
      passage_id: "s1",
      ordinal: 0,
      region: "body",
      back_type: null,
      section_number: "1",
      section_title: "Introduction",
      text: "A synthetic sentence.",
      page_start: 1,
      page_end: 1,
    },
    {
      passage_id: "s2",
      ordinal: 1,
      region: "body",
      back_type: null,
      section_number: "2",
      section_title: "Methods",
      text: "Second   section text,  exactly as stored.",
      page_start: null,
      page_end: null,
    },
  ],
};

const DOC = `/api/documents/${ID}`;
const POLL = 5;

async function chooseAndUpload(name = "paper.pdf"): Promise<void> {
  const user = userEvent.setup();
  await user.upload(
    screen.getByLabelText(/pdf file/i),
    new File(["%PDF-1.4"], name, { type: "application/pdf" }),
  );
  await user.click(screen.getByRole("button", { name: /upload and parse/i }));
}

// --- Upload ------------------------------------------------------------------

describe("upload", () => {
  it("uploads, shows the real status while processing, then the structure", async () => {
    on("POST", "/api/documents", ok({ ...documentBody(), created: true }, 202));
    on("GET", DOC, ok(documentBody({ status: "processing" })), ok(documentBody({ status: "parsed" })));
    on("GET", `${DOC}/structure`, ok(STRUCTURE));
    render(<App pollIntervalMs={POLL} />);

    await chooseAndUpload();

    expect(await screen.findByText("Processing")).toBeTruthy();
    expect(await screen.findByRole("heading", { name: "A Synthetic Paper" })).toBeTruthy();
    expect(screen.getByText("Parsed")).toBeTruthy();
    expect(window.location.search).toBe(`?document=${ID}`);
  });

  it("asks for a file when none is chosen and sends nothing", async () => {
    render(<App pollIntervalMs={POLL} />);

    await userEvent.setup().click(screen.getByRole("button", { name: /upload and parse/i }));

    expect(screen.getByText("Choose a PDF file first.")).toBeTruthy();
    expect(calls).toEqual([]);
  });

  it("shows the server's plain-language reason when the upload is rejected", async () => {
    on("POST", "/api/documents", ok({ error: { code: "not_pdf", message: "The file is not a PDF. Only PDF files can be uploaded." } }, 415));
    render(<App pollIntervalMs={POLL} />);

    await chooseAndUpload("notes.pdf");

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("The file is not a PDF.");
    expect(window.location.search).toBe("");
  });

  it("says when the same file was uploaded before", async () => {
    on("POST", "/api/documents", ok({ ...documentBody({ status: "parsed" }), created: false }));
    on("GET", DOC, ok(documentBody({ status: "parsed" })));
    on("GET", `${DOC}/structure`, ok(STRUCTURE));
    render(<App pollIntervalMs={POLL} />);

    await chooseAndUpload();

    expect(await screen.findByText(/uploaded before/i)).toBeTruthy();
  });
});

// --- Document states -----------------------------------------------------

describe("document view", () => {
  it("shows passages exactly as stored, with section and page or 'page unknown'", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    on("GET", DOC, ok(documentBody({ status: "parsed" })));
    on("GET", `${DOC}/structure`, ok(STRUCTURE));
    render(<App pollIntervalMs={POLL} />);

    const methods = await screen.findByRole("region", { name: "2 Methods" });
    expect(within(methods).getByText("page unknown")).toBeTruthy();
    expect(
      within(methods).getByText((_, element) =>
        element?.textContent === "Second   section text,  exactly as stored." &&
        element.tagName === "P",
      ),
    ).toBeTruthy();
    const intro = screen.getByRole("region", { name: "1 Introduction" });
    expect(within(intro).getByText("page 1")).toBeTruthy();
    expect(screen.getByText("Ada B Example, Ben Sample")).toBeTruthy();
    expect(screen.getByText("No DOI found by the parser")).toBeTruthy();
  });

  it("shows a failure with its explanation and retries on request", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    const failed = documentBody({
      status: "failed",
      failure_reason: "no_text_layer",
      failure_explanation: "No text was found in the PDF.",
    });
    on("GET", DOC, ok(failed));
    on("POST", `${DOC}/retry`, ok(failed, 202));
    render(<App pollIntervalMs={POLL} />);

    expect(await screen.findByText("Failed")).toBeTruthy();
    expect(screen.getByText("No text was found in the PDF.")).toBeTruthy();
    expect(screen.getByText("no_text_layer")).toBeTruthy();

    on("GET", DOC, ok(documentBody({ status: "processing" })), ok(documentBody({ status: "parsed" })));
    on("GET", `${DOC}/structure`, ok(STRUCTURE));
    await userEvent.setup().click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByRole("heading", { name: "A Synthetic Paper" })).toBeTruthy();
    expect(calls).toContain(`POST ${DOC}/retry`);
  });

  it("explains an unknown document id", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    on("GET", DOC, ok({ error: { code: "document_not_found", message: "No document has this id." } }, 404));
    render(<App pollIntervalMs={POLL} />);

    expect(await screen.findByText("No document has this id.")).toBeTruthy();
    expect(screen.getByRole("link", { name: /upload a pdf/i })).toBeTruthy();
    // Trying again cannot help: the id does not exist.
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
  });

  it("explains an unreachable server and can try again", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    on("GET", DOC, "network_error", ok(documentBody({ status: "failed", failure_reason: "parser_busy", failure_explanation: "The PDF parser was busy." })));
    render(<App pollIntervalMs={POLL} />);

    expect(await screen.findByText(/couldn't reach the paperpilot server/i)).toBeTruthy();
    await userEvent.setup().click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText("The PDF parser was busy.")).toBeTruthy();
  });

  it("stops polling once the document is finished", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    on("GET", DOC, ok(documentBody({ status: "pending" })), ok(documentBody({ status: "failed", failure_reason: "parser_busy", failure_explanation: "Busy." })));
    render(<App pollIntervalMs={POLL} />);

    await screen.findByText("Busy.");
    const count = calls.length;
    await new Promise((resolve) => setTimeout(resolve, POLL * 10));

    expect(calls.length).toBe(count);
  });
});
