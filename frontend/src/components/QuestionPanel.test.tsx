import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AnswerResponse, EvidencePassage, StatementResponse } from "../api/types";
import { QuestionPanel } from "./QuestionPanel";

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
    text: "Stored   passage text.",
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
    retrieval_method: "keyword_full_text",
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

async function ask(question = "Why did it retreat?"): Promise<void> {
  const user = userEvent.setup();
  render(<QuestionPanel documentId={DOCUMENT_ID} />);
  await user.type(screen.getByLabelText("Your question"), question);
  await user.click(screen.getByRole("button", { name: "Ask" }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("asking", () => {
  it("sends the question scoped to this document", async () => {
    respond(200, answer());

    await ask("A question?");
    await screen.findByText("Ice retreated.");

    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/answers");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      question: "A question?",
      document_ids: [DOCUMENT_ID],
    });
  });

  it("asks for a question when the box is blank and sends nothing", async () => {
    respond(200, answer());
    const user = userEvent.setup();
    render(<QuestionPanel documentId={DOCUMENT_ID} />);

    await user.type(screen.getByLabelText("Your question"), "   ");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(screen.getByRole("alert").textContent).toContain("Enter a question first.");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("shows the real step while waiting, without a percentage", async () => {
    let finish: (value: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>((resolve) => (finish = resolve))),
    );

    await ask();

    const waiting = screen.getByRole("status");
    expect(waiting.textContent).toMatch(/searching this paper/i);
    expect(waiting.textContent).not.toMatch(/%/);
    finish(new Response(JSON.stringify(answer()), { status: 200 }));
    await screen.findByText("Ice retreated.");
  });

  it("shows the server's message and keeps the question after an error", async () => {
    respond(503, {
      error: { code: "model_not_configured", message: "No AI model is configured." },
    });

    await ask("Keep me");

    expect((await screen.findByRole("alert")).textContent).toContain(
      "No AI model is configured.",
    );
    expect((screen.getByLabelText("Your question") as HTMLTextAreaElement).value).toBe(
      "Keep me",
    );
    expect(screen.queryByText(/citations checked/i)).toBeNull();
  });
});

describe("a validated answer", () => {
  it("shows statements, a valid citation in words, and a link to its evidence", async () => {
    respond(200, answer());

    await ask();

    await screen.findByText("Ice retreated.");
    expect(screen.getByText("Citations checked")).toBeTruthy();
    const link = screen.getByRole("link", { name: /P1.*Valid/ });
    expect(link.getAttribute("href")).toBe("#evidence-P1");
    expect(screen.getByText(/retreated quickly/)).toBeTruthy();
  });

  it("does not claim the passages support the statements (FR-CIT-005)", async () => {
    respond(200, answer());

    await ask();

    await screen.findByText("Ice retreated.");
    const notice = screen.getByText("Citations checked").closest(".answer-status");
    expect(notice?.textContent).toMatch(/does not confirm/i);
    expect(screen.getByText(/Claim support: not evaluated/)).toBeTruthy();
  });

  it("shows evidence as stored, with its section and page from the response", async () => {
    respond(200, answer());

    await ask();

    const panel = await screen.findByRole("region", { name: "Evidence" });
    expect(within(panel).getByText("2 Results")).toBeTruthy();
    expect(within(panel).getByText("page 4")).toBeTruthy();
    expect(within(panel).getByText("A Paper")).toBeTruthy();
    expect(
      within(panel).getByText(
        (_, element) =>
          element?.tagName === "P" && element.textContent === "Stored   passage text.",
      ),
    ).toBeTruthy();
    expect(panel.querySelector("#evidence-P1")).toBeTruthy();
  });

  it("says when a page or section is unknown", async () => {
    respond(
      200,
      answer({ evidence: [evidence({ section: null, page_start: null, page_end: null })] }),
    );

    await ask();

    const panel = await screen.findByRole("region", { name: "Evidence" });
    expect(within(panel).getByText("page unknown")).toBeTruthy();
    expect(within(panel).getByText("section unknown")).toBeTruthy();
  });

  it("labels a partial answer and shows its limitations", async () => {
    respond(
      200,
      answer({ evidence_sufficiency: "partial", limitations: "Only one study." }),
    );

    await ask();

    expect(await screen.findByText(/covers only part of the question/i)).toBeTruthy();
    expect(screen.getByText("Only one study.")).toBeTruthy();
  });

  it("reports what produced the answer", async () => {
    respond(200, answer({ passages_dropped: 1 }));

    await ask();

    const details = await screen.findByText(/Claim support: not evaluated/);
    expect(details.textContent).toContain("fake-model");
    expect(details.textContent).toContain("answer-v1");
    expect(details.textContent).toContain("2 passages retrieved");
    expect(details.textContent).toContain("1 dropped");
  });
});

describe("a failed answer", () => {
  const failed = answer({
    validation_status: "failed",
    evidence: [],
    statements: [
      statement({
        text: "An unverified claim.",
        has_valid_citation: false,
        citations: [
          { alias: "P9", quote: null, valid: false, reason: "passage_not_found", passage_id: null },
        ],
      }),
    ],
  });

  it("is visibly marked and not presented as evidence-backed (FR-UI-003)", async () => {
    respond(200, failed);

    await ask();

    expect(await screen.findByText("Citations failed checks")).toBeTruthy();
    expect(screen.getByText(/do not treat this answer as evidence-backed/i)).toBeTruthy();
    expect(screen.queryByText("Citations checked")).toBeNull();
    expect(screen.getByText("Not verified")).toBeTruthy();
  });

  it("does not link a failed citation to evidence", async () => {
    respond(200, failed);

    await ask();

    await screen.findByText("An unverified claim.");
    expect(screen.queryByRole("link", { name: /P9/ })).toBeNull();
    expect(screen.queryByRole("region", { name: "Evidence" })).toBeNull();
  });

  it("does not call anything evidence when the answer failed", async () => {
    respond(200, { ...failed, evidence: [evidence()] });

    await ask();

    await screen.findByText("An unverified claim.");
    expect(screen.queryByRole("region", { name: "Evidence" })).toBeNull();
    expect(
      screen.getByRole("region", { name: "Passages behind the valid citations only" }),
    ).toBeTruthy();
  });

  it.each([
    ["passage_not_found", "Not found"],
    ["not_in_context", "Not shown to the model"],
    ["wrong_paper", "Outside the selected paper"],
    ["quote_mismatch", "Quote not in passage"],
  ] as const)("explains %s in words", async (reason, label) => {
    respond(
      200,
      answer({
        validation_status: "failed",
        evidence: [],
        statements: [
          statement({
            has_valid_citation: false,
            citations: [{ alias: "P2", quote: null, valid: false, reason, passage_id: null }],
          }),
        ],
      }),
    );

    await ask();

    expect(await screen.findByText(new RegExp(`P2.*${label}`))).toBeTruthy();
  });

  it("marks a statement that has no citation", async () => {
    respond(
      200,
      answer({
        validation_status: "failed",
        evidence: [],
        statements: [statement({ has_valid_citation: false, citations: [] })],
      }),
    );

    await ask();

    expect(await screen.findByText("No citation")).toBeTruthy();
  });
});

describe("not enough evidence", () => {
  it("is a plain answer with no statements or evidence", async () => {
    respond(
      200,
      answer({
        statements: [],
        evidence: [],
        evidence_sufficiency: "insufficient",
        limitations: "The passages do not cover this.",
      }),
    );

    await ask();

    expect(await screen.findByText("Not enough evidence")).toBeTruthy();
    expect(screen.getByText("The passages do not cover this.")).toBeTruthy();
    expect(screen.queryByText("Citations checked")).toBeNull();
    expect(screen.queryByRole("region", { name: "Evidence" })).toBeNull();
  });

  it("says when no AI model was used", async () => {
    respond(
      200,
      answer({
        statements: [],
        evidence: [],
        evidence_sufficiency: "insufficient",
        limitations: "No passages matched.",
        model: null,
        prompt_version: null,
        retrieved_passage_ids: [],
      }),
    );

    await ask();

    expect(await screen.findByText(/No AI model was used/)).toBeTruthy();
  });
});
