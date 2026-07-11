import { ImagePlus, Trash2, Upload } from "lucide-react";
import { useId, useRef, useState } from "react";
import { resolveMediaUrl } from "@/features/competitions";
import { cn } from "@/shared/lib";
import { Button, IconButton } from "@/shared/ui";

interface PosterUploadFieldProps {
  value: string;
  disabled?: boolean;
  uploading?: boolean;
  error?: string;
  onUpload: (file: File) => Promise<void>;
  onClear: () => void;
}

const ACCEPT = "image/jpeg,image/png,image/webp";

export function PosterUploadField({
  value,
  disabled = false,
  uploading = false,
  error,
  onUpload,
  onClear,
}: PosterUploadFieldProps): React.JSX.Element {
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
    if (!ACCEPT.split(",").includes(file.type)) {
      setLocalError("Допустимы только JPEG, PNG или WebP.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setLocalError("Размер файла не должен превышать 5 МБ.");
      return;
    }
    try {
      await onUpload(file);
    } catch {
      setLocalError("Не удалось загрузить афишу.");
    }
  };

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-foreground" id={`${inputId}-label`}>
        Афиша конкурса
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
          <div className="relative aspect-[3/4] max-h-80 w-full bg-muted/30">
            <img src={previewUrl} alt="Афиша конкурса" className="size-full object-contain" />
            {!disabled ? (
              <div className="absolute top-2 right-2 flex gap-2">
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
                  aria-label="Удалить афишу"
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
            className="flex aspect-[3/4] max-h-80 w-full flex-col items-center justify-center gap-3 px-4 text-center outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ImagePlus className="size-8 text-muted-foreground" aria-hidden="true" />
            <span className="font-medium text-sm">
              {uploading ? "Загрузка…" : "Загрузить афишу"}
            </span>
            <span className="text-muted-foreground text-xs">
              Перетащите файл сюда или нажмите для выбора. JPEG, PNG или WebP до 5 МБ.
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
