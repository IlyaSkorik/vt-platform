import { useCallback, useEffect, useRef } from "react";

/** Long enough that a typed word is one save, short enough to feel automatic. */
const DEFAULT_DELAY_MS = 700;

export type Autosave<T> = {
  /** Hold this payload for `delayMs`; a newer one replaces it and restarts the wait. */
  schedule: (payload: T) => void;
  /** Send whatever is waiting right now (nothing happens if nothing is). */
  flush: () => void;
  /** Drop what is waiting — the edit that caused it is no longer worth saving. */
  cancel: () => void;
};

/**
 * Debounced autosave that outlives the field.
 *
 * Saving per keystroke would send a name the backend refuses ("И" on the way to
 * "Иванова"), so the write waits out a pause in typing. That wait used to die with
 * the component: collapsing a performance card, opening another one or leaving the
 * page cleared the timer and the last seconds of typing were never sent — the field
 * came back the way the server still remembered it, as if it had been wiped.
 *
 * Here the pending write is flushed instead of dropped, both when the field unmounts
 * and when the page is being hidden (`pagehide` — closing the tab or switching app
 * on a phone, the last moment a request can still be started).
 */
export function useAutosave<T>(
  save: (payload: T) => void,
  delayMs = DEFAULT_DELAY_MS,
): Autosave<T> {
  const saveRef = useRef(save);
  saveRef.current = save;
  // Boxed, so that a payload which is itself nullable still reads as "one is waiting".
  const pending = useRef<{ payload: T } | null>(null);
  const timer = useRef<number | null>(null);

  const clearTimer = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);

  const flush = useCallback(() => {
    clearTimer();
    const waiting = pending.current;
    if (waiting === null) {
      return;
    }
    pending.current = null;
    saveRef.current(waiting.payload);
  }, [clearTimer]);

  const cancel = useCallback(() => {
    clearTimer();
    pending.current = null;
  }, [clearTimer]);

  const schedule = useCallback(
    (payload: T) => {
      pending.current = { payload };
      clearTimer();
      timer.current = window.setTimeout(flush, delayMs);
    },
    [clearTimer, delayMs, flush],
  );

  useEffect(() => {
    const onPageHide = (): void => flush();
    window.addEventListener("pagehide", onPageHide);
    return () => {
      window.removeEventListener("pagehide", onPageHide);
      flush();
    };
  }, [flush]);

  return { schedule, flush, cancel };
}
