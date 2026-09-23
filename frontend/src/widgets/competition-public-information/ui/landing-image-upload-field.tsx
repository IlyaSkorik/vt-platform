import { ImagePlus, Trash2, Upload } from "lucide-react";
import { useId, useRef, useState } from "react";
import { resolveMediaUrl } from "@/features/competitions";
import { cn } from "@/shared/lib";
import { Button, IconButton } from "@/shared/ui";

const ACCEPT = "image/jpeg,image/png,image/webp";

interface LandingImageUploadFieldProps {
  label: string;
  value: string | null | undefined;
  disabled?: boolean;
  uploading?: boolean;
  /** Ratio of the frame — the same one the public landing crops this image to. */
  aspectClassName?: string;
  /** Caps the frame's width; the height follows from the ratio, never the other
   * way round. A `max-h-*` cap would silently widen the frame past its ratio and
   * show a crop the festival page never renders. */
  widthClassName?: string;
  /** `cover` crops to the frame (photos), `contain` fits the whole image inside
   * it (logos) — matching how the public page renders each kind. */
  fit?: "cover" | "contain";
  hint?: string;
  onUpload: (file: File) => Promise<void>;
  onClear: () => void;
}

export function LandingImageUploadField({
  label,
  value,
  disabled = false,
  uploading = false,
  aspectClassName = "aspect-[4/3]",
  widthClassName = "max-w-sm",
  fit = "cover",
  hint,
  onUpload,
  onClear,
}: LandingImageUploadFieldProps): React.JSX.Element {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const previewUrl = resolveMediaUrl(value);

  const pickFile = async (file: File | undefined): Promise<void> => {
    setLocalError(null);
    if (!file) return;
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
      setLocalError("Не удалось загрузить изображение.");
    }
  };

  return (
    <div className="space-y-2">
      <p className="font-medium text-foreground text-sm" id={`${inputId}-label`}>
        {label}
      </p>
      <fieldset
        aria-labelledby={`${inputId}-label`}
        className={cn(
          "relative m-0 block overflow-hidden rounded-md border border-dashed bg-muted/20 p-0 transition-colors",
          widthClassName,
          isDragging && "border-ring bg-accent/40",
          localError && "border-danger",
          disabled && "opacity-60",
        )}
        onDragEnter={(event) => {
          event.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          event.preventDefault();
          setIsDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragging(false);
          if (!disabled) void pickFile(event.dataTransfer.files[0]);
        }}
      >
        {previewUrl ? (
          <div className={cn("relative w-full bg-muted/30", aspectClassName)}>
            <img
              src={previewUrl}
              alt=""
              className={cn("size-full", fit === "contain" ? "object-contain" : "object-cover")}
            />
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
                  aria-label={`Удалить: ${label}`}
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
            className={cn(
              "flex w-full flex-col items-center justify-center gap-2 px-4 text-center outline-none focus-visible:ring-2 focus-visible:ring-ring",
              aspectClassName,
            )}
          >
            <ImagePlus className="size-7 text-muted-foreground" aria-hidden="true" />
            <span className="font-medium text-sm">
              {uploading ? "Загрузка…" : "Загрузить фото"}
            </span>
            <span className="text-muted-foreground text-xs">JPEG, PNG или WebP до 5 МБ</span>
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
      {localError ? <p className="text-danger text-sm">{localError}</p> : null}
      {hint && !localError ? <p className="text-muted-foreground text-xs">{hint}</p> : null}
    </div>
  );
}
