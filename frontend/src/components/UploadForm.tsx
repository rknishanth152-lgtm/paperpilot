// Upload one PDF (FR-ING-001, FR-UI-001). The server decides whether the file
// is acceptable; this form only sends it and shows the server's answer.

import { useId, useState, type DragEvent, type FormEvent } from "react";

import { ApiError, uploadDocument } from "../api/client";
import type { UploadResponse } from "../api/types";
import { formatBytes } from "../lib/format";
import { Icon } from "./Icon";

export function UploadForm({ onUploaded }: { onUploaded: (upload: UploadResponse) => void }) {
  const inputId = useId();
  const hintId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);

  function choose(next: File | null): void {
    setFile(next);
    setProblem(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (uploading) return;
    if (file === null) {
      setProblem("Choose a PDF file first.");
      return;
    }
    setUploading(true);
    setProblem(null);
    try {
      onUploaded(await uploadDocument(file));
    } catch (error) {
      setProblem(
        error instanceof ApiError ? error.message : "The upload failed. Try again.",
      );
      setUploading(false);
    }
  }

  function drop(event: DragEvent<HTMLLabelElement>): void {
    event.preventDefault();
    setDragging(false);
    choose(event.dataTransfer.files[0] ?? null);
  }

  return (
    <form className="panel upload" onSubmit={submit} noValidate>
      <h1 className="upload-title">Upload a paper</h1>
      <p className="muted" id={hintId}>
        One PDF at a time. It is parsed on this computer by GROBID; the file is not sent
        anywhere else.
      </p>

      <label
        htmlFor={inputId}
        className={dragging ? "dropzone dropzone-active" : "dropzone"}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={drop}
      >
        <span className="dropzone-label">PDF file</span>
        {file ? (
          <span className="dropzone-file">
            <Icon name="file" />
            <span className="dropzone-name">{file.name}</span>
            <span className="muted">{formatBytes(file.size)}</span>
          </span>
        ) : (
          <span className="dropzone-empty">
            <Icon name="upload" />
            Choose a file, or drop it here
          </span>
        )}
        <input
          id={inputId}
          className="visually-hidden"
          type="file"
          accept="application/pdf,.pdf"
          aria-describedby={hintId}
          onChange={(event) => choose(event.target.files?.[0] ?? null)}
        />
      </label>

      {problem && (
        <p className="form-error" role="alert">
          <Icon name="alert" />
          {problem}
        </p>
      )}

      <div className="actions">
        <button type="submit" className="button button-primary" aria-busy={uploading}>
          {uploading ? "Uploading…" : "Upload and parse"}
        </button>
      </div>
    </form>
  );
}
