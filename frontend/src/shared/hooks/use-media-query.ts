import { useEffect, useState } from "react";

/**
 * Subscribe to a CSS media query and re-render on change.
 *
 * Mobile-first is a platform tenet (ARCH-001 §4.5); this hook lets components
 * adapt behaviour (not just styling) to viewport and user preferences.
 *
 * @example const isDesktop = useMediaQuery("(min-width: 1024px)");
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === "undefined" || !window.matchMedia) {
      return false;
    }
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) {
      return;
    }
    const mediaQueryList = window.matchMedia(query);
    const listener = (event: MediaQueryListEvent): void => setMatches(event.matches);

    setMatches(mediaQueryList.matches);
    mediaQueryList.addEventListener("change", listener);
    return () => mediaQueryList.removeEventListener("change", listener);
  }, [query]);

  return matches;
}
