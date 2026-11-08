import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getDocument, retryDocument, uploadDocument } from "./client";

function respond(status: number, body: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("uploadDocument", () => {
  it("sends the file as the body with the percent-encoded name", async () => {
    respond(202, { document_id: "d1", status: "pending", created: true });
    const file = new File(["%PDF-1.4"], "Résumé paper.pdf", { type: "application/pdf" });

    await uploadDocument(file);

    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/documents");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(file);
    expect((init.headers as Record<string, string>)["X-Filename"]).toBe(
      "R%C3%A9sum%C3%A9%20paper.pdf",
    );
  });

  it("turns the error envelope into an ApiError with code and message", async () => {
    respond(415, { error: { code: "not_pdf", message: "The file is not a PDF." } });

    const error = await uploadDocument(new File(["x"], "a.pdf")).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 415, code: "not_pdf", message: "The file is not a PDF." });
  });
});

describe("errors that are not from the API", () => {
  it("reports an unreachable server in plain language", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );

    const error = await getDocument("d1").catch((e: unknown) => e);

    expect(error).toMatchObject({ code: "network_error" });
    expect((error as ApiError).message).toMatch(/couldn't reach/i);
  });

  it("does not show a body that is not the error envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("<html>Bad gateway: internal detail</html>", { status: 502 })),
    );

    const error = await getDocument("d1").catch((e: unknown) => e);

    expect(error).toMatchObject({ status: 502, code: "unexpected_response" });
    expect((error as ApiError).message).not.toMatch(/internal detail/);
    expect((error as ApiError).message).toMatch(/check that the backend is running/i);
  });
});

describe("retryDocument", () => {
  it("posts to the retry address", async () => {
    respond(202, { document_id: "d 1", status: "failed" });

    await retryDocument("d 1");

    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/documents/d%201/retry");
    expect(init.method).toBe("POST");
  });
});
