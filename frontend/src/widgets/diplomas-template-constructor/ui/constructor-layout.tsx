import type { TemplateDocument } from "@/features/diplomas";
import { ConstructorToolbar } from "./constructor-toolbar";
import { ElementPalette } from "./element-palette";
import { PdfCanvas } from "./pdf-canvas";
import { PropertiesPanel } from "./properties-panel";

interface TemplateConstructorLayoutProps {
  templateName: string;
  /** The backing PDF, when one is attached. None in the current milestone. */
  document?: TemplateDocument;
}

/**
 * The full-page constructor workspace: a top toolbar over a three-column body
 * (element palette · PDF canvas · properties). A standalone editor surface — no
 * modals — so it can grow into a Figma/Canva-style layout editor.
 */
export function TemplateConstructorLayout({
  templateName,
  document,
}: TemplateConstructorLayoutProps): React.JSX.Element {
  return (
    <div className="-mx-4 -mt-4 flex min-h-[calc(100svh-8rem)] flex-col overflow-hidden rounded-lg border bg-background md:-mx-6 md:-mt-6 lg:-mx-8">
      <ConstructorToolbar templateName={templateName} hasDocument={document != null} />
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <ElementPalette />
        <PdfCanvas {...(document?.url ? { pdfUrl: document.url } : {})} />
        <PropertiesPanel />
      </div>
    </div>
  );
}
