import { FileText, Upload } from "lucide-react";
import { Button, EmptyState } from "@/shared/ui";
import { PdfViewer } from "./pdf-viewer";

interface PdfCanvasProps {
  /** Resolved PDF URL when a document is attached; empty state otherwise. */
  pdfUrl?: string;
  onRequestUpload: () => void;
  isUploading: boolean;
}

export function PdfCanvas({
  pdfUrl,
  onRequestUpload,
  isUploading,
}: PdfCanvasProps): React.JSX.Element {
  if (pdfUrl) {
    return (
      <section
        aria-label="Просмотр PDF шаблона"
        className="flex min-w-0 flex-1 flex-col bg-muted/40"
      >
        <PdfViewer url={pdfUrl} />
      </section>
    );
  }

  return (
    <section
      aria-label="Просмотр PDF шаблона"
      className="flex min-w-0 flex-1 items-center justify-center overflow-auto bg-muted/40 p-6"
    >
      <div className="max-w-md">
        <EmptyState
          icon={<FileText className="size-6" aria-hidden="true" />}
          title="PDF шаблон не загружен"
          description="Загрузите PDF, чтобы начать разметку диплома."
          action={
            <Button onClick={onRequestUpload} disabled={isUploading}>
              <Upload className="size-4" aria-hidden="true" />
              {isUploading ? "Загрузка…" : "Загрузить PDF"}
            </Button>
          }
        />
      </div>
    </section>
  );
}
