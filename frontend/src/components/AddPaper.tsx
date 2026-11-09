// Add one PDF. The server decides whether the file is acceptable (FR-ING-001);
// this only sends it and shows the answer.

import { FilePlus2, LoaderCircle, TriangleAlert, Upload } from "lucide-react";
import { useState, type DragEvent, type ReactNode } from "react";

import { ApiError, uploadDocument } from "../api/client";
import type { UploadResponse } from "../api/types";

interface Props {
  onAdded: (upload: UploadResponse) => void;
  large?: boolean;
}

export function AddPaper({ onAdded, large = false }: Props) {
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  async function send(file: File | undefined): Promise<void> {
    if (!file || busy) return;
    setBusy(true);
    setProblem(null);
    try {
      onAdded(await uploadDocument(file));
    } catch (error) {
      setProblem(error instanceof ApiError ? error.message : "That paper couldn't be added. Try again.");
    } finally {
      setBusy(false);
    }
  }

  function drop(event: DragEvent<HTMLLabelElement>): void {
    event.preventDefault();
    setDragging(false);
    void send(event.dataTransfer.files[0]);
  }

  const input: ReactNode = (
    <input
      className="visually-hidden"
      type="file"
      accept="application/pdf,.pdf"
      aria-label="Add a paper"
      onChange={(event) => {
        void send(event.target.files?.[0]);
        event.target.value = "";
      }}
    />
  );

  return (
    <div>
      {large ? (
        <label
          className="dropzone"
          data-dragging={dragging}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={drop}
        >
          {busy ? <LoaderCircle className="icon spin" size={22} /> : <Upload className="icon" size={22} />}
          <strong>{busy ? "Adding your paper…" : "Choose a PDF, or drop it here"}</strong>
          {input}
        </label>
      ) : (
        <label className="add-paper">
          {busy ? <LoaderCircle className="icon spin" size={18} /> : <FilePlus2 className="icon" size={18} />}
          {busy ? "Adding…" : "Add a paper"}
          {input}
        </label>
      )}
      {problem && (
        <p className="alert small add-message" role="alert">
          <TriangleAlert className="icon" size={16} />
          {problem}
        </p>
      )}
    </div>
  );
}
