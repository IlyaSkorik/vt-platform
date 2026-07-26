import { FileText } from "lucide-react";
import { useMemo, useState } from "react";
import { Document, Page } from "react-pdf";
import { useCompetitionsList } from "@/features/competitions";
import {
  createBindingResolver,
  type DocumentType,
  resolveFieldDisplay,
  type TemplateField,
  usePreviewApplications,
  usePreviewBindings,
} from "@/features/diplomas";
import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  Select,
  type SelectOption,
  Spinner,
} from "@/shared/ui";
import "../lib/pdf-worker";
import { PreviewFieldRenderer } from "./preview-field-renderer";

const TARGET_WIDTH = 720;

interface PreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  fields: TemplateField[];
  /** The template's kind — decides how values are formatted in the preview. */
  documentType: DocumentType;
  pdfUrl?: string;
}

/**
 * Diploma preview: pick a competition + application, then render the template
 * over the PDF with that application's real values (via the BindingResolver).
 * View-only — a check before any mass generation.
 */
export function PreviewDialog({
  open,
  onOpenChange,
  fields,
  documentType,
  pdfUrl,
}: PreviewDialogProps): React.JSX.Element {
  const [competitionId, setCompetitionId] = useState("");
  const [applicationId, setApplicationId] = useState("");
  const [shownApplicationId, setShownApplicationId] = useState("");

  const competitionsQuery = useCompetitionsList();
  const applicationsQuery = usePreviewApplications(competitionId || undefined);
  const bindingsQuery = usePreviewBindings(shownApplicationId || undefined, documentType);

  const competitionOptions: SelectOption[] = useMemo(
    () => (competitionsQuery.data ?? []).map((item) => ({ value: item.id, label: item.title })),
    [competitionsQuery.data],
  );
  const applicationOptions: SelectOption[] = useMemo(
    () => (applicationsQuery.data ?? []).map((item) => ({ value: item.id, label: item.label })),
    [applicationsQuery.data],
  );

  function handleOpenChange(next: boolean): void {
    onOpenChange(next);
    if (!next) {
      setCompetitionId("");
      setApplicationId("");
      setShownApplicationId("");
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Предпросмотр диплома</DialogTitle>
        </DialogHeader>

        {shownApplicationId ? (
          <PreviewCanvas
            fields={fields}
            pdfUrl={pdfUrl}
            bindings={bindingsQuery.data}
            loading={bindingsQuery.isLoading}
          />
        ) : (
          <div className="flex flex-col gap-4">
            <Select
              label="Конкурс"
              placeholder="Выберите конкурс"
              options={competitionOptions}
              value={competitionId}
              onValueChange={(value) => {
                setCompetitionId(value);
                setApplicationId("");
              }}
            />
            <Select
              label="Заявка"
              placeholder={competitionId ? "Выберите заявку" : "Сначала выберите конкурс"}
              options={applicationOptions}
              value={applicationId}
              onValueChange={setApplicationId}
              disabled={!competitionId || applicationsQuery.isLoading}
            />
          </div>
        )}

        <DialogFooter>
          {shownApplicationId ? (
            <>
              <Button variant="outline" onClick={() => setShownApplicationId("")}>
                Назад
              </Button>
              <Button onClick={() => handleOpenChange(false)}>Закрыть</Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => handleOpenChange(false)}>
                Отмена
              </Button>
              <Button
                disabled={!applicationId}
                onClick={() => setShownApplicationId(applicationId)}
              >
                Показать
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface PreviewCanvasProps {
  fields: TemplateField[];
  pdfUrl: string | undefined;
  bindings: Record<string, string> | undefined;
  loading: boolean;
}

function PreviewCanvas({
  fields,
  pdfUrl,
  bindings,
  loading,
}: PreviewCanvasProps): React.JSX.Element {
  const [numPages, setNumPages] = useState(0);
  const [scale, setScale] = useState(1);
  const resolve = useMemo(() => createBindingResolver(bindings ?? {}), [bindings]);

  if (!pdfUrl) {
    return (
      <EmptyState
        icon={<FileText className="size-6" aria-hidden="true" />}
        title="PDF не загружен"
        description="Загрузите PDF шаблона, чтобы увидеть предпросмотр диплома."
      />
    );
  }

  return (
    <div className="scrollbar-custom max-h-[70vh] overflow-auto rounded-md bg-muted/40 p-4">
      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : null}
      <Document
        file={pdfUrl}
        onLoadSuccess={({ numPages: count }) => setNumPages(count)}
        loading={
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        }
        error={<p className="py-12 text-center text-danger text-sm">Не удалось загрузить PDF.</p>}
        className="mx-auto flex w-fit flex-col items-center gap-4"
      >
        {Array.from({ length: numPages }, (_, index) => index + 1).map((pageNumber) => (
          <div key={pageNumber} className="relative shadow-elevation-1">
            <Page
              pageNumber={pageNumber}
              scale={scale}
              renderTextLayer={false}
              renderAnnotationLayer={false}
              onLoadSuccess={(page) => {
                if (pageNumber === 1) {
                  setScale(TARGET_WIDTH / page.originalWidth);
                }
              }}
            />
            <div className="pointer-events-none absolute inset-0">
              {fields
                .filter((field) => field.page === pageNumber)
                .map((field) => {
                  // Unresolved bindings → null → field omitted (no placeholder).
                  const displayValue = resolveFieldDisplay(field, resolve);
                  if (displayValue === null) {
                    return null;
                  }
                  return (
                    <PreviewFieldRenderer
                      key={field.id}
                      field={field}
                      scale={scale}
                      displayValue={displayValue}
                    />
                  );
                })}
            </div>
          </div>
        ))}
      </Document>
    </div>
  );
}
