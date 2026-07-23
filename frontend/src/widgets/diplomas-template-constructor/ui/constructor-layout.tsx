import { useRef } from "react";
import {
  type DiplomaTemplate,
  resolveMediaUrl,
  type TemplateField,
  useUploadTemplateDocumentMutation,
} from "@/features/diplomas";
import { ApiError } from "@/shared/api";
import { toast } from "@/shared/ui";
import { ConstructorFieldsProvider, useConstructorFieldsContext } from "../model/fields-context";
import { PreviewDataProvider } from "../model/preview-context";
import { useLayoutPersistence } from "../model/use-layout-persistence";
import { ConstructorToolbar } from "./constructor-toolbar";
import { ElementPalette } from "./element-palette";
import { FieldShortcuts } from "./field-shortcuts";
import { PdfCanvas } from "./pdf-canvas";
import { PropertiesPanel } from "./properties-panel";
import { UnsavedChangesGuard } from "./unsaved-changes-guard";

interface TemplateConstructorLayoutProps {
  template: DiplomaTemplate;
  /** The saved layout, loaded before the editor mounts. */
  initialFields: TemplateField[];
}

/**
 * Sets up the editor's shared state (seeded with the saved layout) and renders
 * the workspace inside it. Mount this keyed by template id so switching templates
 * gives a fresh editor.
 */
export function TemplateConstructorLayout({
  template,
  initialFields,
}: TemplateConstructorLayoutProps): React.JSX.Element {
  return (
    <ConstructorFieldsProvider initialFields={initialFields}>
      <ConstructorWorkspace template={template} />
    </ConstructorFieldsProvider>
  );
}

/**
 * The workspace shell: toolbar over the three-column body. Owns the PDF upload
 * and layout-save flows and wires the unsaved-changes guard. Reads editor state
 * (fields, dirty) from context; never mutates geometry itself.
 */
function ConstructorWorkspace({ template }: { template: DiplomaTemplate }): React.JSX.Element {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadTemplateDocumentMutation();
  const persistence = useLayoutPersistence(template.id);
  const { fields, dirty, markPristine } = useConstructorFieldsContext();

  const pdfUrl = resolveMediaUrl(template.document?.fileReference);

  const requestUpload = (): void => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
    const file = event.target.files?.[0];
    // Reset so re-selecting the same file fires change again.
    event.target.value = "";
    if (!file) {
      return;
    }
    if (file.type !== "application/pdf") {
      toast.error("Поддерживается только PDF.");
      return;
    }
    try {
      await upload.mutateAsync({ templateId: template.id, file });
      toast.success("PDF загружен");
    } catch (error) {
      toast.error(errorMessage(error, "Не удалось загрузить PDF."));
    }
  };

  const handleSave = async (): Promise<void> => {
    try {
      await persistence.save(fields);
      markPristine();
      toast.success("Все изменения сохранены");
    } catch (error) {
      toast.error(errorMessage(error, "Не удалось сохранить макет."));
    }
  };

  return (
    <PreviewDataProvider>
      <div className="-mx-4 -mt-4 flex min-h-[calc(100svh-8rem)] flex-col overflow-hidden rounded-lg border bg-background md:-mx-6 md:-mt-6 lg:-mx-8">
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(event) => void handleFileChange(event)}
        />
        <UnsavedChangesGuard when={dirty} />
        <FieldShortcuts />
        <ConstructorToolbar
          templateName={template.name}
          hasDocument={template.document != null}
          onRequestUpload={requestUpload}
          isUploading={upload.isPending}
          onSave={() => void handleSave()}
          isSaving={persistence.isSaving}
          dirty={dirty}
        />
        <div className="flex min-h-0 flex-1 flex-col md:flex-row">
          <ElementPalette />
          <PdfCanvas
            {...(pdfUrl ? { pdfUrl } : {})}
            onRequestUpload={requestUpload}
            isUploading={upload.isPending}
          />
          <PropertiesPanel />
        </div>
      </div>
    </PreviewDataProvider>
  );
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? (error.problem?.detail ?? fallback) : fallback;
}
