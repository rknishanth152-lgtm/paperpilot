// Whether there is room for all three areas side by side.

import { useEffect, useState } from "react";

const QUERY = "(min-width: 64rem)";

function matches(): boolean {
  return typeof window.matchMedia === "function" ? window.matchMedia(QUERY).matches : true;
}

export function useIsWide(): boolean {
  const [wide, setWide] = useState(matches);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia(QUERY);
    const onChange = (): void => setWide(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  return wide;
}
