// Calls to the backend document API. Every failure becomes an ApiError with a
// stable code and a plain-language message; raw response bodies and exception
// text are never shown to the user (NFR-SEC-005).

import type { DocumentResponse, StructureResponse, UploadResponse } from "./types";

// Same-origin path; the Vite dev server forwards it to the backend.
const BASE = "/api/documents";

export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string;
  readonly details: Record<string, unknown> | null;

  constructor(
    status: number | null,
    code: string,
    message: string,
    details: Record<string, unknown> | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface ErrorEnvelope {
  error: { code: string; message: string; details?: Record<string, unknown> };
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error = (value as { error: unknown }).error;
  return (
    typeof error === "object" &&
    error !== null &&
    typeof (error as { code?: unknown }).code === "string" &&
    typeof (error as { message?: unknown }).message === "string"
  );
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new ApiError(
      null,
      "network_error",
      "Couldn't reach the PaperPilot server. Check that the backend is running, then try again.",
    );
  }
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (response.ok) return body as T;
  if (isErrorEnvelope(body)) {
    throw new ApiError(
      response.status,
      body.error.code,
      body.error.message,
      body.error.details ?? null,
    );
  }
  throw new ApiError(
    response.status,
    "unexpected_response",
    // The backend always sends the envelope, so this came from something in
    // between, such as the dev proxy when the backend is stopped.
    "The PaperPilot server did not respond properly. Check that the backend is running, then try again.",
  );
}

export function uploadDocument(file: File): Promise<UploadResponse> {
  return request<UploadResponse>(BASE, {
    method: "POST",
    body: file,
    headers: {
      "Content-Type": "application/pdf",
      "X-Filename": encodeURIComponent(file.name),
    },
  });
}

export function getDocument(documentId: string): Promise<DocumentResponse> {
  return request<DocumentResponse>(`${BASE}/${encodeURIComponent(documentId)}`);
}

export function getStructure(documentId: string): Promise<StructureResponse> {
  return request<StructureResponse>(`${BASE}/${encodeURIComponent(documentId)}/structure`);
}

export function retryDocument(documentId: string): Promise<DocumentResponse> {
  return request<DocumentResponse>(`${BASE}/${encodeURIComponent(documentId)}/retry`, {
    method: "POST",
  });
}
