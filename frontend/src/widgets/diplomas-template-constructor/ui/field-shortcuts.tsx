import { useEffect } from "react";
import { useConstructorFieldsContext } from "../model/fields-context";

function isTypingTarget(target: EventTarget | null): boolean {
  const element = target as HTMLElement | null;
  if (element === null) {
    return false;
  }
  return element.tagName === "INPUT" || element.tagName === "TEXTAREA" || element.isContentEditable;
}

/**
 * FieldShortcuts: the editor's keyboard infrastructure. Renders nothing.
 *   Delete / Backspace — remove the active field
 *   Escape            — clear the selection
 *   Ctrl/Cmd + D      — duplicate the active field
 * Ignored while typing in a form control.
 */
export function FieldShortcuts(): null {
  const { selectedId, removeField, duplicateField, deselect } = useConstructorFieldsContext();

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      if (isTypingTarget(event.target)) {
        return;
      }
      if (event.key === "Escape") {
        deselect();
        return;
      }
      if (selectedId === null) {
        return;
      }
      if (event.key === "Delete" || event.key === "Backspace") {
        event.preventDefault();
        removeField(selectedId);
        return;
      }
      if ((event.ctrlKey || event.metaKey) && (event.key === "d" || event.key === "D")) {
        event.preventDefault();
        duplicateField(selectedId);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [selectedId, removeField, duplicateField, deselect]);

  return null;
}
