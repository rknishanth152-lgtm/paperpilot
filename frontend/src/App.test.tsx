import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { LibraryDocument, StructureResponse } from "./api/types";

type Reply = { status: number; body: unknown } | "network_error";
let replies: Map<string, Reply[]>;
let calls: string[];

function on(method: string, path: string, ...queue: Reply[]): void {
  replies.set(`${method} ${path}`, queue);
}

function ok(body: unknown, status = 200): Reply {
  return { status, body };
}

const ID = "0190a1b2-0000-7000-8000-000000000001";
const LIST = "/api/documents";
const STRUCTURE_URL = `${LIST}/${ID}/structure`;
const ASSESS = `${LIST}/${ID}/assessment`;
const POLL = 5;
const NOT_RUN = {
  status: 404,
  body: { error: { code: "assessment_not_found", message: "Not checked yet." } },
};

function row(overrides: Partial<LibraryDocument> = {}): LibraryDocument {
  return {
    document_id: ID,
    status: "parsed",
    failure_explanation: null,
    original_filename: "paper.pdf",
    title: "A Synthetic Paper",
    created_at: "2026-11-04T10:00:00Z",
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
  ],
};

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
      const reply = queue.length > 1 ? queue.shift()! : queue[0]!;
      if (reply === "network_error") throw new TypeError("Failed to fetch");
      return new Response(JSON.stringify(reply.body), { status: reply.status });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function ready(): void {
  on("GET", LIST, ok({ documents: [row()] }));
  on("GET", STRUCTURE_URL, ok(STRUCTURE));
  on("GET", ASSESS, NOT_RUN);
}

async function upload(name = "paper.pdf"): Promise<void> {
  await userEvent
    .setup()
    .upload(
      screen.getAllByLabelText(/add a paper/i)[0] as HTMLInputElement,
      new File(["%PDF-1.4"], name, { type: "application/pdf" }),
    );
}

describe("the library", () => {
  it("invites you to add a paper when it is empty", async () => {
    on("GET", LIST, ok({ documents: [] }));

    render(<App pollIntervalMs={POLL} />);

    expect(await screen.findByText(/your library is empty/i)).toBeTruthy();
    expect(screen.getByRole("heading", { name: /start with a paper/i })).toBeTruthy();
  });

  it("lists papers by title, in plain status words", async () => {
    on(
      "GET",
      LIST,
      ok({
        documents: [
          row(),
          row({ document_id: "b", status: "processing", title: null, original_filename: "x.pdf" }),
          row({ document_id: "c", status: "pending", title: null, original_filename: "y.pdf" }),
          row({ document_id: "d", status: "failed", title: null, original_filename: "z.pdf" }),
        ],
      }),
    );

    render(<App pollIntervalMs={POLL} />);

    const library = await screen.findByRole("navigation", { name: "Your library" });
    expect(await within(library).findByText("A Synthetic Paper")).toBeTruthy();
    expect(within(library).getByText("Ready to read")).toBeTruthy();
    expect(within(library).getByText("Reading this paper…")).toBeTruthy();
    expect(within(library).getByText("Waiting to start")).toBeTruthy();
    expect(within(library).getByText("Couldn't read this file")).toBeTruthy();
    expect(within(library).getByText("x.pdf")).toBeTruthy();
  });

  it("opens a paper and keeps it in the address bar", async () => {
    ready();
    render(<App pollIntervalMs={POLL} />);

    await userEvent.setup().click(await screen.findByRole("button", { name: /A Synthetic Paper/ }));

    expect(await screen.findByRole("heading", { level: 2, name: "A Synthetic Paper" })).toBeTruthy();
    expect(window.location.search).toBe(`?document=${ID}`);
  });

  it("shows no internal terms anywhere", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    ready();

    const { container } = render(<App pollIntervalMs={POLL} />);
    await screen.findByText("A synthetic sentence.");
    await screen.findByRole("button", { name: "Run checklist" });

    expect(container.textContent).not.toMatch(/grobid|parsed|parser|sha-256|\bpassage/i);
  });

  it("explains an unreachable server and can try again", async () => {
    on("GET", LIST, "network_error", ok({ documents: [] }));
    render(<App pollIntervalMs={POLL} />);

    expect((await screen.findByRole("alert")).textContent).toMatch(/couldn't reach/i);
    await userEvent.setup().click(screen.getByRole("button", { name: "Try again" }));

    expect(await screen.findByText(/your library is empty/i)).toBeTruthy();
  });

  it("explains a link to a paper that is not in the library", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    on("GET", LIST, ok({ documents: [] }));

    render(<App pollIntervalMs={POLL} />);

    expect(await screen.findByText(/isn't in your library/i)).toBeTruthy();
  });
});

function narrowScreen(): void {
  vi.stubGlobal(
    "matchMedia",
    (query: string) =>
      ({
        matches: false,
        media: query,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      }) as unknown as MediaQueryList,
  );
}

describe("page structure (R10, axe findings)", () => {
  it("has one top-level heading and a main area that the skip link reaches", async () => {
    on("GET", LIST, ok({ documents: [] }));

    render(<App pollIntervalMs={POLL} />);
    await screen.findByText(/your library is empty/i);

    const top = screen.getAllByRole("heading", { level: 1 });
    expect(top.map((heading) => heading.textContent)).toEqual(["PaperPilot"]);
    expect(screen.getByRole("main").id).toBe("main");
    expect(screen.getByRole("link", { name: "Skip to content" }).getAttribute("href")).toBe("#main");
  });

  it("keeps the main area and heading on a narrow screen showing the library", async () => {
    narrowScreen();
    on("GET", LIST, ok({ documents: [row()] }));

    render(<App pollIntervalMs={POLL} />);
    await screen.findByRole("button", { name: /A Synthetic Paper/ });

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("main").id).toBe("main");
  });

  it("names the handles that resize each area", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    ready();

    render(<App pollIntervalMs={POLL} />);
    await screen.findByText("A synthetic sentence.");

    expect(
      screen.getAllByRole("separator").map((handle) => handle.getAttribute("aria-label")),
    ).toEqual(["Resize the library", "Resize the paper"]);
  });

  it("lets the keyboard reach the paper so it can be scrolled", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    ready();

    render(<App pollIntervalMs={POLL} />);
    await screen.findByText("A synthetic sentence.");

    expect(screen.getByRole("region", { name: "The paper" }).getAttribute("tabindex")).toBe("0");
  });
});

describe("adding a paper", () => {
  it("uploads, shows the real wait, then opens the paper", async () => {
    on("GET", LIST, ok({ documents: [] }), ok({ documents: [row({ status: "processing" })] }), ok({ documents: [row()] }));
    on("POST", LIST, ok({ ...row({ status: "pending" }), created: true }, 202));
    on("GET", STRUCTURE_URL, ok(STRUCTURE));
    on("GET", ASSESS, NOT_RUN);
    render(<App pollIntervalMs={POLL} />);
    await screen.findByText(/your library is empty/i);

    await upload();

    expect(await screen.findByText("A synthetic sentence.")).toBeTruthy();
    expect(window.location.search).toBe(`?document=${ID}`);
  });

  it("shows the server's reason when a file is refused", async () => {
    on("GET", LIST, ok({ documents: [] }));
    on("POST", LIST, ok({ error: { code: "not_pdf", message: "This file is not a PDF." } }, 415));
    render(<App pollIntervalMs={POLL} />);
    await screen.findByText(/your library is empty/i);

    await upload("notes.pdf");

    expect((await screen.findByRole("alert")).textContent).toContain("This file is not a PDF.");
    expect(window.location.search).toBe("");
  });

  it("says when the paper is already in the library", async () => {
    ready();
    on("POST", LIST, ok({ ...row(), created: false }));
    render(<App pollIntervalMs={POLL} />);
    await screen.findByRole("button", { name: /A Synthetic Paper/ });

    await upload();

    expect(await screen.findByText(/already in your library/i)).toBeTruthy();
  });
});

describe("a paper that is not ready", () => {
  it("states the real wait and offers no questions yet", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    on("GET", LIST, ok({ documents: [row({ status: "processing" })] }));

    render(<App pollIntervalMs={POLL} />);

    expect((await screen.findAllByText("Reading this paper…")).length).toBeGreaterThan(0);
    expect(screen.queryByRole("tab", { name: "Ask" })).toBeNull();
    expect(screen.getByText(/once this paper is ready/i)).toBeTruthy();
  });

  it("stops checking once the paper has finished", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    on(
      "GET",
      LIST,
      ok({ documents: [row({ status: "pending" })] }),
      ok({ documents: [row({ status: "failed", failure_explanation: "Busy." })] }),
    );
    render(<App pollIntervalMs={POLL} />);

    await screen.findByText("Busy.");
    const count = calls.length;
    await new Promise((resolve) => setTimeout(resolve, POLL * 10));

    expect(calls.length).toBe(count);
  });

  it("explains a failure and tries again on request", async () => {
    window.history.replaceState(null, "", `/?document=${ID}`);
    on(
      "GET",
      LIST,
      ok({ documents: [row({ status: "failed", failure_explanation: "This PDF has no text." })] }),
    );
    on("POST", `${LIST}/${ID}/retry`, ok(row(), 202));
    render(<App pollIntervalMs={POLL} />);

    expect(await screen.findByText("This PDF has no text.")).toBeTruthy();
    on("GET", LIST, ok({ documents: [row()] }));
    on("GET", STRUCTURE_URL, ok(STRUCTURE));
    on("GET", ASSESS, NOT_RUN);
    await userEvent.setup().click(screen.getByRole("button", { name: "Try again" }));

    await waitFor(() => expect(calls).toContain(`POST ${LIST}/${ID}/retry`));
    expect(await screen.findByText("A synthetic sentence.")).toBeTruthy();
  });
});
