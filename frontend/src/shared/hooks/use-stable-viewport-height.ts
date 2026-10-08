import { useEffect, useState } from "react";

/**
 * The viewport height as it was when the page settled, in pixels — frozen
 * against the browser chrome that grows and shrinks under the user's thumb.
 *
 * **The problem this exists for.** `svh`/`dvh` describe a viewport the browser
 * merely *reports* differently as its toolbars collapse. Telegram's in-app
 * browser on iOS does something else: scrolling collapses its header by
 * resizing the web view itself, so the window genuinely gets taller and every
 * viewport unit, `svh` included, recomputes. A band sized to a screenful
 * therefore grows mid-scroll — the artwork behind it re-crops, the content
 * under it jumps, and the page appears to breathe for as long as you scroll.
 * Safari's own address bar does the same thing more gently.
 *
 * **The rule.** Measure once, then ignore every resize that leaves the width
 * alone. A height-only change on a phone is always chrome, never intent. A
 * rotation or a desktop window drag moves the width too, and those are real
 * — the frozen value follows them.
 *
 * Returns `null` until the first layout effect, so the caller can keep a CSS
 * fallback in place and never render a collapsed band on the first paint.
 */
export function useStableViewportHeight(): number | null {
  const [height, setHeight] = useState<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    let width = window.innerWidth;
    setHeight(window.innerHeight);

    const onResize = (): void => {
      if (window.innerWidth === width) {
        return;
      }
      width = window.innerWidth;
      setHeight(window.innerHeight);
    };

    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return height;
}
