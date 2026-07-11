import { FileText, Trash2, Upload } from "lucide-react";
import { useId, useRef, useState } from "react";
import { resolveMediaUrl } from "@/features/competitions";
import { cn } from "@/shared/lib";
import { Button, IconButton } from "@/shared/ui";

interface PdfUploadFieldProps {
  value: string;
  disabled?: boolean;
  uploading?: boolean;
  error?: string;
  onUpload: (file: File) => Promise<void>;
  onClear: () => void;
}

const ACCEPT = "application/pdf";

export function PdfUploadField({
  value,
  disabled = false,
  uploading = false,
  error,
  onUpload,
  onClear,
}: PdfUploadFieldProps): React.JSX.Element {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const previewUrl = resolveMediaUrl(value);
  const message = error ?? localError;

  const pickFile = async (file: File | undefined): Promise<void> => {
    setLocalError(null);
    if (!file) {
      return;
    }
    if (file.type !== ACCEPT && !file.name.toLowerCase().endsWith(".pdf")) {
      setLocalError("Допустим только PDF.");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setLocalError("Размер файла не должен превышать 20 МБ.");
      return;
    }
    try {
      await onUpload(file);
    } catch {
      setLocalError("Не удалось загрузить PDF.");
    }
  };

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-foreground" id={`${inputId}-label`}>
        PDF-файл положения
      </p>

      <fieldset
        aria-labelledby={`${inputId}-label`}
        className={cn(
          "relative m-0 overflow-hidden rounded-md border border-dashed bg-muted/20 p-0 transition-colors",
          isDragging && "border-ring bg-accent/40",
          message && "border-danger",
          disabled && "opacity-60",
        )}
        onDragEnter={(event) => {
          event.preventDefault();
          if (!disabled) {
            setIsDragging(true);
          }
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          event.preventDefault();
          setIsDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          if (!disabled) {
            void pickFile(event.dataTransfer.files[0]);
          }
        }}
      >
        {previewUrl ? (
          <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                <FileText className="size-4" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="truncate font-medium text-sm">PDF загружен</p>
                <a
                  href={previewUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary text-xs underline-offset-2 hover:underline"
                >
                  Открыть файл
                </a>
              </div>
            </div>
            {!disabled ? (
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  loading={uploading}
                  onClick={() => inputRef.current?.click()}
                >
                  <Upload className="size-3.5" aria-hidden="true" />
                  Заменить
                </Button>
                <IconButton
                  type="button"
                  size="sm"
                  variant="outline"
                  aria-label="Удалить PDF"
                  icon={<Trash2 aria-hidden="true" />}
                  onClick={onClear}
                  disabled={uploading}
                />
              </div>
            ) : null}
          </div>
        ) : (
          <button
            type="button"
            disabled={disabled || uploading}
            onClick={() => inputRef.current?.click()}
            className="flex min-h-36 w-full cursor-pointer flex-col items-center justify-center gap-3 px-4 text-center outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Upload className="size-8 text-muted-foreground" aria-hidden="true" />
            <span className="font-medium text-sm">{uploading ? "Загрузка…" : "Загрузить PDF"}</span>
            <span className="text-muted-foreground text-xs">
              Перетащите файл сюда или нажмите для выбора. PDF до 20 МБ.
            </span>
          </button>
        )}
      </fieldset>

      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept={ACCEPT}
        className="sr-only"
        disabled={disabled || uploading}
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          void pickFile(file);
        }}
      />

      {message ? <p className="text-danger text-sm">{message}</p> : null}
    </div>
  );
}
