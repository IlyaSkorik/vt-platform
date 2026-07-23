import { createContext, useContext } from "react";
import type { TemplateField } from "@/features/diplomas";
import { type ConstructorFieldsState, useConstructorFields } from "./use-constructor-fields";

const FieldsContext = createContext<ConstructorFieldsState | null>(null);

/**
 * Owns the editor's field state and shares it across palette, overlay, properties
 * and toolbar. `initialFields` seeds the state once — the provider is mounted only
 * after the saved layout has loaded (and keyed by template), so the layout is
 * restored without an effect.
 */
export function ConstructorFieldsProvider({
  initialFields,
  children,
}: {
  initialFields: TemplateField[];
  children: React.ReactNode;
}): React.JSX.Element {
  const value = useConstructorFields(initialFields);
  return <FieldsContext.Provider value={value}>{children}</FieldsContext.Provider>;
}

export function useConstructorFieldsContext(): ConstructorFieldsState {
  const value = useContext(FieldsContext);
  if (value === null) {
    throw new Error("useConstructorFieldsContext must be used within ConstructorFieldsProvider.");
  }
  return value;
}
