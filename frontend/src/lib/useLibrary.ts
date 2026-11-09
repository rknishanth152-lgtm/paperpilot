// The list of papers, kept current while any paper is still being read (AD-010).
// Nothing here estimates progress: it only repeats the status the server reports.

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, listDocuments } from "../api/client";
import type { LibraryDocument } from "../api/types";

export interface Library {
  documents: LibraryDocument[] | null;
  problem: string | null;
  refresh: () => Promise<void>;
}

function isBusy(documents: LibraryDocument[]): boolean {
  return documents.some((d) => d.status === "pending" || d.status === "processing");
}

export function useLibrary(pollIntervalMs: number): Library {
  const [documents, setDocuments] = useState<LibraryDocument[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const active = useRef(true);

  const refresh = useCallback(async (): Promise<void> => {
    clearTimeout(timer.current);
    try {
      const { documents: next } = await listDocuments();
      if (!active.current) return;
      setDocuments(next);
      setProblem(null);
      if (isBusy(next)) {
        timer.current = setTimeout(() => void refresh(), pollIntervalMs);
      }
    } catch (error) {
      if (active.current) {
        setProblem(error instanceof ApiError ? error.message : "Your library couldn't be loaded.");
      }
    }
  }, [pollIntervalMs]);

  useEffect(() => {
    active.current = true;
    void refresh();
    return () => {
      active.current = false;
      clearTimeout(timer.current);
    };
  }, [refresh]);

  return { documents, problem, refresh };
}
