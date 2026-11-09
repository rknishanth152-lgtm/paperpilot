import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AnswerResponse, EvidencePassage, StatementResponse } from "../api/types";
import { AskPane } from "./AskPane";

const DOCUMENT_ID = "0190a1b2-0000-7000-8000-000000000001";

function evidence(overrides: Partial<EvidencePassage> = {}): EvidencePassage {
  return {
    alias: "P1",
    passage_id: "pass-1",
    document_id: DOCUMENT_ID,
    paper_id: "paper-1",
    paper_title: "A Paper",
    section: "2 Results",
    page_start: 4,
    page_end: 4,
    text: "Stored text retreated quickly here.",
    ...overrides,
  };
}

function statement(overrides: Partial<StatementResponse> = {}): StatementResponse {
  return {
    text: "Ice retreated.",
    has_valid_citation: true,
    citations: [
      { alias: "P1", quote: "retreated quickly", valid: true, reason: null, passage_id: "pass-1" },
    ],
    ...overrides,
  };
}

function answer(overrides: Partial<AnswerResponse> = {}): AnswerResponse {
  return {
    statements: [statement()],
    evidence: [evidence()],
    evidence_sufficiency: "sufficient",
    limitations: null,
    validation_status: "validated",
    claim_support: "not_evaluated",
    retrieved_passage_ids: ["pass-1", "pass-2"],
    passages_dropped: 0,
    retrieval_method: "semantic_cosine",
    model: "fake-model",
    prompt_version: "answer-v1",
    ...overrides,
  };
}

function respond(status: number, body: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  );
}

async function ask(onCite = vi.fn(), question = "Why did it retreat?") {
  const user = userEvent.setup();
  render(<AskPane documentId={DOCUMENT_ID} onCite={onCite} />);
  await user.type(screen.getByRole("textbox", { name: "Ask about this paper" }), question);
  await user.click(screen.getByRole("button", { name: "Ask" }));
  return user;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("asking", () => {
  it("invites a first question", () => {
    render(<AskPane documentId={DOCUMENT_ID} onCite={vi.fn()} />);

    expect(screen.getByText(/links to the sentence it came from/i)).toBeTruthy();
  });

  it("sends the question for this paper and keeps it on screen", async () => {
    respond(200, answer());

    await ask(vi.fn(), "A question?");

    expect(await screen.findByText("A question?")).toBeTruthy();
    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/answers");
    expect(JSON.parse(init.body as string)).toEqual({
      question: "A question?",
      document_ids: [DOCUMENT_ID],
    });
  });

  it("asks for text before sending", async () => {
    respond(200, answer());
    render(<AskPane documentId={DOCUMENT_ID} onCite={vi.fn()} />);

    await userEvent.setup().click(screen.getByRole("button", { name: "Ask" }));

    expect(screen.getByRole("alert").textContent).toMatch(/type a question/i);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("states the wait while asking", async () => {
    let finish: (value: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            finish = resolve;
          }),
      ),
    );

    await ask();

    expect(screen.getByRole("status").textContent).toMatch(/reading this paper/i);
    finish(new Response(JSON.stringify(answer()), { status: 200 }));
    await screen.findByText("Ice retreated.");
  });

  it("sends only one question at a time", async () => {
    let finish: (value: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () =>
          new Promise<Response>((resolve) => {
            finish = resolve;
          }),
      ),
    );
    const user = await ask();

    await user.type(screen.getByRole("textbox", { name: "Ask about this paper" }), "Another?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(fetch).toHaveBeenCalledTimes(1);
    finish(new Response(JSON.stringify(answer()), { status: 200 }));
    await screen.findByText("Ice retreated.");
  });

  it("shows a server failure in plain words", async () => {
    respond(429, { error: { code: "model_rate_limited", message: "Too many requests." } });

    await ask();

    expect((await screen.findByRole("alert")).textContent).toContain("Too many requests.");
  });

  it("keeps earlier answers when asking again", async () => {
    respond(200, answer());
    const user = await ask();
    await screen.findByText("Ice retreated.");

    await user.type(screen.getByRole("textbox", { name: "Ask about this paper" }), "Second?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Second?")).toBeTruthy();
    expect(screen.getByText("Why did it retreat?")).toBeTruthy();
  });
});

describe("a checked answer", () => {
  it("says what the check means and does not claim proof", async () => {
    respond(200, answer());

    await ask();

    expect(await screen.findByText(/every quote above was found in this paper/i)).toBeTruthy();
    expect(screen.getByText(/for you to judge/i)).toBeTruthy();
  });

  it("opens the exact source from a citation", async () => {
    respond(200, answer());
    const onCite = vi.fn();
    const user = await ask(onCite);

    await user.click(await screen.findByRole("button", { name: "Open source 1 in the paper" }));

    expect(onCite).toHaveBeenCalledWith("pass-1", "retreated quickly");
  });

  it("lists sources with their stored location", async () => {
    respond(200, answer());

    await ask();

    expect(await screen.findByRole("button", { name: /2 Results, page 4/ })).toBeTruthy();
  });

  it("says when a location is unknown", async () => {
    respond(200, answer({ evidence: [evidence({ section: null, page_start: null, page_end: null })] }));

    await ask();

    expect(await screen.findByRole("button", { name: /section unknown, page unknown/ })).toBeTruthy();
  });

  it("numbers repeated sources once", async () => {
    respond(200, answer({ statements: [statement(), statement({ text: "Again." })] }));

    await ask();

    await screen.findByText("Again.");
    expect(screen.getAllByRole("button", { name: "Open source 1 in the paper" })).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Open source 2 in the paper" })).toBeNull();
  });

  it("tucks technical details away until asked", async () => {
    respond(200, answer());
    const user = await ask();

    await user.click(await screen.findByRole("button", { name: "How this answer was made" }));

    const details = await screen.findByText(/fake-model/);
    expect(details.textContent).toContain("2 parts of this paper");
    expect(details.textContent).toContain("by meaning");
    expect(details.textContent).toContain("answer-v1");
  });

  it("names keyword search when it was used", async () => {
    respond(200, answer({ retrieval_method: "keyword_full_text" }));
    const user = await ask();

    await user.click(await screen.findByRole("button", { name: "How this answer was made" }));

    expect((await screen.findByText(/fake-model/)).textContent).toContain("by matching words");
  });
});

describe("answers that must not look proven", () => {
  it("warns plainly when a source could not be confirmed", async () => {
    respond(
      200,
      answer({
        validation_status: "failed",
        statements: [
          statement({
            has_valid_citation: false,
            citations: [
              { alias: "P1", quote: "changed", valid: false, reason: "quote_mismatch", passage_id: null },
            ],
          }),
        ],
        evidence: [],
      }),
    );

    await ask();

    expect(await screen.findByText(/some sources couldn't be confirmed/i)).toBeTruthy();
    expect(screen.getByText(/quote not found in the paper/i)).toBeTruthy();
    expect(screen.queryByText(/every quote above/i)).toBeNull();
    expect(screen.queryByRole("button", { name: /open source/i })).toBeNull();
  });

  it("says plainly when the paper has no answer", async () => {
    respond(
      200,
      answer({
        statements: [],
        evidence: [],
        evidence_sufficiency: "insufficient",
        limitations: "The paper does not cover this.",
      }),
    );

    await ask();

    expect(await screen.findByText(/not enough evidence/i)).toBeTruthy();
    expect(screen.getByText("The paper does not cover this.")).toBeTruthy();
    expect(screen.queryByText(/every quote above/i)).toBeNull();
  });

  it("says when an answer covers only part of the question", async () => {
    respond(200, answer({ evidence_sufficiency: "partial", limitations: "Only one study." }));

    await ask();

    expect(await screen.findByText(/only part of your question/i)).toBeTruthy();
    expect(screen.getByText("Only one study.")).toBeTruthy();
  });
});
