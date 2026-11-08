import { describe, expect, it } from "vitest";

import type { Passage } from "../api/types";
import { formatBytes, formatPages, groupPassages, sectionLabel } from "./format";

function passage(overrides: Partial<Passage>): Passage {
  return {
    passage_id: crypto.randomUUID(),
    ordinal: 0,
    region: "body",
    back_type: null,
    section_number: null,
    section_title: null,
    text: "Text.",
    page_start: 1,
    page_end: 1,
    ...overrides,
  };
}

describe("formatPages", () => {
  it("shows one page", () => {
    expect(formatPages(3, 3)).toBe("page 3");
  });

  it("shows a page range", () => {
    expect(formatPages(2, 4)).toBe("pages 2–4");
  });

  it("says unknown when the page is null, never 0 (DR-007)", () => {
    expect(formatPages(null, null)).toBe("page unknown");
    expect(formatPages(null, 2)).toBe("page unknown");
  });

  it("treats a missing end as a single page", () => {
    expect(formatPages(5, null)).toBe("page 5");
  });
});

describe("sectionLabel", () => {
  it("joins number and title", () => {
    expect(sectionLabel(passage({ section_number: "2.1", section_title: "Data" }))).toBe(
      "2.1 Data",
    );
  });

  it("names regions without a section title", () => {
    expect(sectionLabel(passage({ region: "abstract" }))).toBe("Abstract");
    expect(sectionLabel(passage({ region: "caption" }))).toBe("Figure and table captions");
    expect(sectionLabel(passage({ region: "back", back_type: "acknowledgement" }))).toBe(
      "Back matter: acknowledgement",
    );
    expect(sectionLabel(passage({ region: "body" }))).toBe("Untitled section");
  });

  it("prefers the stored section title for back matter", () => {
    expect(
      sectionLabel(passage({ region: "back", back_type: "funding", section_title: "Funding" })),
    ).toBe("Funding");
  });
});

describe("groupPassages", () => {
  it("groups consecutive passages with the same label, keeping order", () => {
    const passages = [
      passage({ ordinal: 0, region: "abstract" }),
      passage({ ordinal: 1, section_title: "Intro" }),
      passage({ ordinal: 2, section_title: "Intro" }),
      passage({ ordinal: 3, section_title: "Methods" }),
      passage({ ordinal: 4, section_title: "Intro" }),
    ];

    const groups = groupPassages(passages);

    expect(groups.map((group) => group.label)).toEqual([
      "Abstract",
      "Intro",
      "Methods",
      "Intro",
    ]);
    expect(groups.flatMap((group) => group.passages.map((p) => p.ordinal))).toEqual([
      0, 1, 2, 3, 4,
    ]);
  });

  it("returns no groups for no passages", () => {
    expect(groupPassages([])).toEqual([]);
  });
});

describe("formatBytes", () => {
  it("uses KB and MB", () => {
    expect(formatBytes(512)).toBe("512 bytes");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});
