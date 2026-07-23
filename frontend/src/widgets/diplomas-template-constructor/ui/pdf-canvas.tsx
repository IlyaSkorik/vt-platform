import { FileText, Upload } from "lucide-react";
import { Button, EmptyState } from "@/shared/ui";

interface PdfCanvasProps {
  /** Resolved PDF URL when a document is attached; empty state otherwise. */
  pdfUrl?: string;
}

export function PdfCanvas({ pdfUrl }: PdfCanvasProps): React.JSX.Element {
  return (
    <section
      aria-label="Просмотр PDF шаблона"
      className="flex min-w-0 flex-1 items-center justify-center overflow-auto bg-muted/40 p-6"
    >
      {pdfUrl ? (
        // View-only first page: no field placement, no drag & drop yet.
        <div className="aspect-[1/1.414] h-full max-h-full w-auto max-w-full overflow-hidden rounded-md border border-border bg-white shadow-elevation-1">
          <object
            data={pdfUrl}
            type="application/pdf"
            className="size-full"
            aria-label="PDF, страница 1"
          >
            <p className="p-4 text-muted-foreground text-sm">Не удалось отобразить PDF.</p>
          </object>
        </div>
      ) : (
        <div className="max-w-md">
          <EmptyState
            icon={<FileText className="size-6" aria-hidden="true" />}
            title="PDF шаблон не загружен"
            description="Загрузите PDF, чтобы начать разметку диплома."
            action={
              <Button disabled>
                <Upload className="size-4" aria-hidden="true" />
                Загрузить PDF
              </Button>
            }
          />
        </div>
      )}
    </section>
  );
}
