import { useEffect, useState } from "react";
import { useBlocker } from "react-router";

interface UnsavedChangesGuardResult {
  isBlocked: boolean;
  proceed: () => void;
  reset: () => void;
}

/**
 * Blocks in-app navigation and tab close while `isDirty` is true.
 * Callers render a confirmation dialog when `isBlocked` is true.
 */
export function useUnsavedChangesGuard(isDirty: boolean): UnsavedChangesGuardResult {
  const blocker = useBlocker(isDirty);
  const [isBlocked, setIsBlocked] = useState(false);

  useEffect(() => {
    setIsBlocked(blocker.state === "blocked");
  }, [blocker.state]);

  useEffect(() => {
    if (!isDirty) {
      return;
    }

    const onBeforeUnload = (event: BeforeUnloadEvent): void => {
      event.preventDefault();
      event.returnValue = "";
    };

    window.addEventListener("beforeunload", onBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
    };
  }, [isDirty]);

  return {
    isBlocked,
    proceed: () => {
      if (blocker.state === "blocked") {
        blocker.proceed();
      }
      setIsBlocked(false);
    },
    reset: () => {
      if (blocker.state === "blocked") {
        blocker.reset();
      }
      setIsBlocked(false);
    },
  };
}
