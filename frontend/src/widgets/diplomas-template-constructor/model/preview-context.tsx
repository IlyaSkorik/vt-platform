import { createContext, useContext, useMemo, useState } from "react";
import {
  type DocumentType,
  type PreviewMode,
  resolvePreviewValue,
  type TemplateFieldBinding,
} from "@/features/diplomas";

interface PreviewData {
  mode: PreviewMode;
  setMode: (mode: PreviewMode) => void;
  /** Resolve a binding to its sample display value, or null when there is none. */
  resolve: (binding: TemplateFieldBinding) => string | null;
}

const PreviewContext = createContext<PreviewData | null>(null);

/**
 * PreviewDataProvider: supplies the sample values fields show while editing and
 * lets the editor flip between a solo participant and a collective. At
 * generation time a real data provider replaces this; the renderer is unaware.
 *
 * Takes the template's ``documentType`` because some samples differ by kind — a
 * thank-you letter prints a teacher's name without the role a diploma states.
 */
export function PreviewDataProvider({
  documentType,
  children,
}: {
  documentType: DocumentType | string;
  children: React.ReactNode;
}): React.JSX.Element {
  const [mode, setMode] = useState<PreviewMode>("individual");
  const value = useMemo<PreviewData>(
    () => ({
      mode,
      setMode,
      resolve: (binding) => resolvePreviewValue(binding, mode, documentType),
    }),
    [mode, documentType],
  );
  return <PreviewContext.Provider value={value}>{children}</PreviewContext.Provider>;
}

export function usePreviewData(): PreviewData {
  const value = useContext(PreviewContext);
  if (value === null) {
    throw new Error("usePreviewData must be used within a PreviewDataProvider.");
  }
  return value;
}
