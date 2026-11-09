import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Passage, StructureResponse } from "../api/types";
import { locateQuote } from "../lib/quote";
import { PaperPane } from "./PaperPane";

const ID = "doc-1";

function passage(overrides: Partial<Passage> = {}): Passage {
  return {
    passage_id: "s1",
    ordinal: 0,
    region: "body",
    back_type: null,
    section_number: "1",
    section_title: "Introduction",
    text: "A stored sentence about ice.",
    page_start: 2,
    page_end: 2,
    ...overrides,
  };
}

function structure(passages: Passage[], title: string | null = "A Paper"): StructureResponse {
  return {
    document_id: ID,
    status: "parsed",
    parser: { name: "grobid", version: "1" },
    page_count: 2,
    paper: { paper_id: "p", title, authors: ["Ada Example"], abstract: null, doi: "10.1/x" },
    passages,
  };
}

function serve(body: unknown, status = 200): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("locateQuote", () => {
  it("finds an exact quote", () => {
    expect(locateQuote("one two three", "two")).toEqual([4, 7]);
  });

  it("ignores spacing differences", () => {
    expect(locateQuote("fi ndings  are here", "findings are")).toEqual([0, 14]);
  });

  it("keeps case, and finds nothing otherwise", () => {
    expect(locateQuote("One two", "one")).toBeNull();
    expect(locateQuote("One two", "   ")).toBeNull();
  });
});

describe("the paper", () => {
  it("shows the title, authors and text exactly as stored", async () => {
    serve(structure([passage({ text: "Spaced   text,  kept." })]));

    render(<PaperPane documentId={ID} focus={null} />);

    expect(await screen.findByRole("heading", { level: 1, name: "A Paper" })).toBeTruthy();
    expect(screen.getByText("Ada Example")).toBeTruthy();
    expect(
      screen.getByText((_, element) => element?.textContent === "Spaced   text,  kept." && element.tagName === "P"),
    ).toBeTruthy();
    expect(screen.getByRole("heading", { name: "1 Introduction" })).toBeTruthy();
  });

  it("shows the stored page, or says it is unknown", async () => {
    serve(
      structure([
        passage(),
        passage({ passage_id: "s2", ordinal: 1, page_start: null, page_end: null }),
      ]),
    );

    render(<PaperPane documentId={ID} focus={null} />);

    expect(await screen.findByText("page 2")).toBeTruthy();
    expect(screen.getByText("page unknown")).toBeTruthy();
  });

  it("says when no title was found", async () => {
    serve(structure([passage()], null));

    render(<PaperPane documentId={ID} focus={null} />);

    expect(await screen.findByRole("heading", { level: 1, name: "Untitled paper" })).toBeTruthy();
  });

  it("explains a loading failure", async () => {
    serve({ error: { code: "internal_error", message: "It broke." } }, 500);

    render(<PaperPane documentId={ID} focus={null} />);

    expect((await screen.findByRole("alert")).textContent).toContain("It broke.");
  });
});

describe("following a citation", () => {
  it("highlights the exact quote and scrolls to it", async () => {
    serve(structure([passage()]));
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;

    render(<PaperPane documentId={ID} focus={{ passageId: "s1", quote: "sentence about", tick: 1 }} />);

    expect((await screen.findByText("sentence about")).tagName).toBe("MARK");
    expect(scroll).toHaveBeenCalled();
  });

  it("highlights the whole paragraph when the quote cannot be located", async () => {
    serve(structure([passage()]));

    render(<PaperPane documentId={ID} focus={{ passageId: "s1", quote: "elsewhere", tick: 1 }} />);

    expect((await screen.findByText("A stored sentence about ice.")).tagName).toBe("MARK");
  });

  it("highlights the whole paragraph when there is no quote", async () => {
    serve(structure([passage()]));

    render(<PaperPane documentId={ID} focus={{ passageId: "s1", quote: null, tick: 1 }} />);

    expect((await screen.findByText("A stored sentence about ice.")).tagName).toBe("MARK");
  });

  it("marks only the cited paragraph", async () => {
    serve(structure([passage(), passage({ passage_id: "s2", ordinal: 1, text: "Other text." })]));

    render(<PaperPane documentId={ID} focus={{ passageId: "s1", quote: null, tick: 1 }} />);

    expect((await screen.findByText("Other text.")).tagName).toBe("P");
  });
});
