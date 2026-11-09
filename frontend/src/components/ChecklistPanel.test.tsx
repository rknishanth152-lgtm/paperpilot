import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AssessmentItem, AssessmentResponse } from "../api/types";
import { ChecklistPanel } from "./ChecklistPanel";

const DOCUMENT_ID = "0190a1b2-0000-7000-8000-000000000001";
const URL = `/api/documents/${DOCUMENT_ID}/assessment`;

function item(overrides: Partial<AssessmentItem> = {}): AssessmentItem {
  return {
    key: "code_availability",
    title: "Code availability",
    question: "Does the paper say how a reader can obtain the code?",
    status: "reported",
    status_label: "Reported",
    status_description: "The passages state this.",
    review_reason: null,
    explanation: "A link is given.",
    passages_examined: 8,
    evidence: [
      {
        passage_id: "pass-1",
        section: "5 Methods",
        page_start: 3,
        page_end: 4,
        quote: "code is at example.org",
        text: "Our code is at example.org for everyone.",
      },
    ],
    ...overrides,
  };
}

function assessment(overrides: Partial<AssessmentResponse> = {}): AssessmentResponse {
  return {
    assessment_id: "assess-1",
    document_id: DOCUMENT_ID,
    checklist_version: "checklist-v1",
    document_status: "parsed",
    model: "fake-model",
    prompt_version: "reproducibility-v1",
    retrieval_method: "semantic_cosine",
    created_at: "2026-11-09T10:00:00Z",
    items: [item()],
    ...overrides,
  };
}

const NOT_FOUND = item({
  key: "software_environment",
  title: "Software",
  status: "not_found",
  status_label: "Not found in the material examined",
  status_description: "The passages examined do not contain this. It does not mean the paper omits it.",
  explanation: null,
  evidence: [],
});
const REVIEW = item({
  key: "data_preparation",
  title: "Data preparation",
  status: "needs_review",
  status_label: "Needs review",
  status_description: "The evidence could not be verified.",
  review_reason: "evidence_unverified",
  explanation: null,
  evidence: [],
});

function envelope(code: string, message: string): unknown {
  return { error: { code, message } };
}

function server(replies: Record<string, { status: number; body: unknown }>): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const reply = replies[`${init?.method ?? "GET"} ${url}`];
      if (!reply) throw new Error(`unexpected ${init?.method ?? "GET"} ${url}`);
      return new Response(JSON.stringify(reply.body), { status: reply.status });
    }),
  );
}

const NONE_YET = { status: 404, body: envelope("assessment_not_found", "None yet.") };

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("before a run", () => {
  it("loads without running anything and offers to run", async () => {
    server({ [`GET ${URL}`]: NONE_YET });

    render(<ChecklistPanel documentId={DOCUMENT_ID} />);

    expect(await screen.findByRole("button", { name: "Run checklist" })).toBeTruthy();
    expect(vi.mocked(fetch).mock.calls).toHaveLength(1);
    expect(screen.getByText(/not a score or a judgement/i)).toBeTruthy();
    expect(screen.getByText(/sent to the configured AI provider/i)).toBeTruthy();
  });

  it("shows an error from loading in plain words and can still run", async () => {
    server({ [`GET ${URL}`]: { status: 500, body: envelope("internal_error", "It broke.") } });

    render(<ChecklistPanel documentId={DOCUMENT_ID} />);

    expect((await screen.findByRole("alert")).textContent).toContain("It broke.");
    expect(screen.getByRole("button", { name: "Run checklist" })).toBeTruthy();
  });
});

describe("a saved assessment", () => {
  it("states each status in words next to its item", async () => {
    server({
      [`GET ${URL}`]: { status: 200, body: assessment({ items: [item(), NOT_FOUND, REVIEW] }) },
    });

    render(<ChecklistPanel documentId={DOCUMENT_ID} />);

    const row = (await screen.findByRole("heading", { name: "Software" })).closest("li");
    expect(row).toBeTruthy();
    expect(within(row as HTMLElement).getByText("Not found in the material examined")).toBeTruthy();
    expect(screen.getByText("Reported")).toBeTruthy();
    expect(screen.getByText("Needs review")).toBeTruthy();
    expect(screen.getByText("The evidence could not be verified.")).toBeTruthy();
  });

  it("shows no count or total that could read as a score", async () => {
    server({
      [`GET ${URL}`]: { status: 200, body: assessment({ items: [item(), NOT_FOUND, REVIEW] }) },
    });

    const { container } = render(<ChecklistPanel documentId={DOCUMENT_ID} />);
    await screen.findByRole("heading", { name: "Software" });

    expect(container.textContent).not.toMatch(/\d+\s*(of|\/)\s*\d+\s*(items|reported)/i);
    expect(container.textContent?.toLowerCase()).not.toMatch(/\bscore:|\bgrade|verdict:/);
  });

  it("shows the quote and its stored location, with the full passage available", async () => {
    server({ [`GET ${URL}`]: { status: 200, body: assessment() } });

    render(<ChecklistPanel documentId={DOCUMENT_ID} />);

    expect((await screen.findByText("code is at example.org")).tagName).toBe("MARK");
    expect(screen.getByText(/5 Methods/)).toBeTruthy();
    expect(screen.getByText(/pages 3–4/)).toBeTruthy();
    expect(screen.getByText("Our code is at example.org for everyone.")).toBeTruthy();
  });

  it("says when a location is unknown", async () => {
    const unknown = item({
      evidence: [
        { passage_id: "p", section: null, page_start: null, page_end: null, quote: "q", text: "t q" },
      ],
    });
    server({ [`GET ${URL}`]: { status: 200, body: assessment({ items: [unknown] }) } });

    render(<ChecklistPanel documentId={DOCUMENT_ID} />);

    expect(await screen.findByText(/section unknown/)).toBeTruthy();
    expect(screen.getByText(/page unknown/)).toBeTruthy();
  });

  it("states what was examined and what produced the result", async () => {
    server({ [`GET ${URL}`]: { status: 200, body: assessment() } });

    render(<ChecklistPanel documentId={DOCUMENT_ID} />);

    expect(await screen.findByText(/8 passages examined/)).toBeTruthy();
    const details = screen.getByText(/checklist-v1/);
    expect(details.textContent).toContain("fake-model");
    expect(details.textContent).toContain("reproducibility-v1");
    expect(details.textContent).toContain("semantic_cosine");
  });

  it("uses the singular for one passage, and says when no model was used", async () => {
    server({
      [`GET ${URL}`]: {
        status: 200,
        body: assessment({
          model: null,
          prompt_version: null,
          retrieval_method: null,
          items: [item({ passages_examined: 1, evidence: [] })],
        }),
      },
    });

    render(<ChecklistPanel documentId={DOCUMENT_ID} />);

    expect(await screen.findByText(/1 passage examined/)).toBeTruthy();
    expect(screen.getByText(/No AI model was used/)).toBeTruthy();
  });

  it("offers to run again", async () => {
    server({ [`GET ${URL}`]: { status: 200, body: assessment() } });

    render(<ChecklistPanel documentId={DOCUMENT_ID} />);

    expect(await screen.findByRole("button", { name: "Run again" })).toBeTruthy();
  });
});

describe("running", () => {
  it("posts, states the real wait, and shows the result", async () => {
    server({
      [`GET ${URL}`]: NONE_YET,
      [`POST ${URL}`]: { status: 200, body: assessment() },
    });
    const user = userEvent.setup();
    render(<ChecklistPanel documentId={DOCUMENT_ID} />);

    await user.click(await screen.findByRole("button", { name: "Run checklist" }));

    expect(await screen.findByRole("heading", { name: "Code availability" })).toBeTruthy();
    const posts = vi.mocked(fetch).mock.calls.filter(([, init]) => init?.method === "POST");
    expect(posts).toHaveLength(1);
  });

  it("does not show a percentage or fake progress while waiting", async () => {
    let finish: (value: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((_: string, init?: RequestInit) =>
        init?.method === "POST"
          ? new Promise<Response>((resolve) => {
              finish = resolve;
            })
          : Promise.resolve(new Response(JSON.stringify(NONE_YET.body), { status: 404 })),
      ),
    );
    const user = userEvent.setup();
    const { container } = render(<ChecklistPanel documentId={DOCUMENT_ID} />);

    await user.click(await screen.findByRole("button", { name: "Run checklist" }));

    expect(screen.getByRole("status").textContent).toMatch(/checking each item/i);
    expect(container.textContent).not.toMatch(/\d+%/);
    finish(new Response(JSON.stringify(assessment()), { status: 200 }));
    await screen.findByRole("heading", { name: "Code availability" });
  });

  it("ignores a second press while running", async () => {
    let finish: (value: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((_: string, init?: RequestInit) =>
        init?.method === "POST"
          ? new Promise<Response>((resolve) => {
              finish = resolve;
            })
          : Promise.resolve(new Response(JSON.stringify(NONE_YET.body), { status: 404 })),
      ),
    );
    const user = userEvent.setup();
    render(<ChecklistPanel documentId={DOCUMENT_ID} />);
    const button = await screen.findByRole("button", { name: "Run checklist" });

    await user.click(button);
    await user.click(screen.getByRole("button", { name: "Checking…" }));

    const posts = vi.mocked(fetch).mock.calls.filter(([, init]) => init?.method === "POST");
    expect(posts).toHaveLength(1);
    finish(new Response(JSON.stringify(assessment()), { status: 200 }));
    await screen.findByRole("heading", { name: "Code availability" });
  });

  it("shows a failure in plain words and keeps the earlier result", async () => {
    server({
      [`GET ${URL}`]: { status: 200, body: assessment() },
      [`POST ${URL}`]: { status: 429, body: envelope("model_rate_limited", "Rate limit reached.") },
    });
    const user = userEvent.setup();
    render(<ChecklistPanel documentId={DOCUMENT_ID} />);

    await user.click(await screen.findByRole("button", { name: "Run again" }));

    expect((await screen.findByRole("alert")).textContent).toContain("Rate limit reached.");
    expect(screen.getByRole("heading", { name: "Code availability" })).toBeTruthy();
  });
});
