import { useEffect } from "react";
import { useBlocker } from "react-router";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui";

interface UnsavedChangesGuardProps {
  /** Block navigation / tab close while there are unsaved changes. */
  when: boolean;
}

/**
 * Guards against losing unsaved layout changes: warns on tab close/reload
 * (native `beforeunload`) and on in-app navigation — back, opening another
 * template, any route change — via react-router's blocker with a confirm dialog.
 */
export function UnsavedChangesGuard({ when }: UnsavedChangesGuardProps): React.JSX.Element {
  const blocker = useBlocker(when);

  useEffect(() => {
    if (!when) {
      return;
    }
    const onBeforeUnload = (event: BeforeUnloadEvent): void => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [when]);

  const blocked = blocker.state === "blocked";

  return (
    <Dialog
      open={blocked}
      onOpenChange={(open) => {
        if (!open) {
          blocker.reset?.();
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Несохранённые изменения</DialogTitle>
          <DialogDescription>
            У вас есть несохранённые изменения. Покинуть страницу?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => blocker.reset?.()}>
            Остаться
          </Button>
          <Button variant="danger" onClick={() => blocker.proceed?.()}>
            Покинуть
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
