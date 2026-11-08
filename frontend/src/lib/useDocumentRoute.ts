// The open document lives in the address bar (`?document=<id>`), so a reload
// or a shared link shows the same document. No router library is needed for
// two views.

import { useCallback, useEffect, useState } from "react";

function readDocumentId(): string | null {
  return new URLSearchParams(window.location.search).get("document");
}

export function useDocumentRoute(): [string | null, (documentId: string | null) => void] {
  const [documentId, setDocumentId] = useState(readDocumentId);

  useEffect(() => {
    const onPopState = (): void => setDocumentId(readDocumentId());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = useCallback((next: string | null) => {
    const url = next === null ? "/" : `/?document=${encodeURIComponent(next)}`;
    window.history.pushState(null, "", url);
    setDocumentId(next);
  }, []);

  return [documentId, navigate];
}
