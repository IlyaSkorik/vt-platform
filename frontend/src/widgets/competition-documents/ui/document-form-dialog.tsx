import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import {
  DOCUMENT_CATEGORY_LABELS,
  DOCUMENT_FORM_CATEGORIES,
  DOCUMENT_VISIBILITIES,
  DOCUMENT_VISIBILITY_LABELS,
  type DocumentFormValues,
  documentFormSchema,
} from "@/features/competitions";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  Select,
  Textarea,
} from "@/shared/ui";
import { DocumentFileField } from "./document-file-field";

interface DocumentFormDialogProps {
  open: boolean;
  mode: "create" | "edit";
  initialValues: DocumentFormValues;
  uploading: boolean;
  submitting: boolean;
  onOpenChange: (open: boolean) => void;
  onUpload: (file: File) => Promise<string>;
  onSubmit: (values: DocumentFormValues) => Promise<void>;
}

export function DocumentFormDialog({
  open,
  mode,
  initialValues,
  uploading,
  submitting,
  onOpenChange,
  onUpload,
  onSubmit,
}: DocumentFormDialogProps): React.JSX.Element {
  const {
    register,
    control,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<DocumentFormValues>({
    resolver: zodResolver(documentFormSchema),
    defaultValues: initialValues,
    mode: "onBlur",
  });

  useEffect(() => {
    if (open) {
      reset(initialValues);
    }
  }, [initialValues, open, reset]);

  const fileReference = watch("fileReference");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="flex max-h-[calc(100dvh-2rem)] max-w-xl flex-col gap-4 overflow-hidden"
        onPointerDownOutside={(event) => {
          // Keep the dialog open while interacting with the portaled Select listbox.
          const target = event.target;
          if (target instanceof Element && target.closest("[data-slot='select-content']")) {
            event.preventDefault();
          }
        }}
        onInteractOutside={(event) => {
          const target = event.target;
          if (target instanceof Element && target.closest("[data-slot='select-content']")) {
            event.preventDefault();
          }
        }}
      >
        <DialogHeader className="shrink-0">
          <DialogTitle>
            {mode === "create" ? "Новый документ" : "Редактирование документа"}
          </DialogTitle>
          <DialogDescription>
            Укажите метаданные и загрузите файл. PDF и изображения можно будет открыть в превью.
          </DialogDescription>
        </DialogHeader>

        <form
          className="flex min-h-0 flex-1 flex-col gap-4"
          onSubmit={handleSubmit(async (values) => {
            await onSubmit(values);
          })}
          noValidate
        >
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain pr-1">
            <Input label="Название" required error={errors.title?.message} {...register("title")} />
            <Textarea
              label="Описание"
              rows={3}
              error={errors.description?.message}
              {...register("description")}
            />

            <Controller
              control={control}
              name="category"
              render={({ field }) => (
                <Select
                  label="Тип документа"
                  required
                  value={field.value}
                  onValueChange={field.onChange}
                  error={errors.category?.message}
                  options={DOCUMENT_FORM_CATEGORIES.map((value) => ({
                    value,
                    label: DOCUMENT_CATEGORY_LABELS[value],
                  }))}
                />
              )}
            />

            <Controller
              control={control}
              name="visibility"
              render={({ field }) => (
                <Select
                  label="Видимость"
                  required
                  value={field.value}
                  onValueChange={field.onChange}
                  error={errors.visibility?.message}
                  options={DOCUMENT_VISIBILITIES.map((value) => ({
                    value,
                    label: DOCUMENT_VISIBILITY_LABELS[value],
                  }))}
                />
              )}
            />

            <Input
              label="Порядок сортировки"
              type="number"
              min={0}
              required
              error={errors.sortOrder?.message}
              {...register("sortOrder", { valueAsNumber: true })}
            />

            <DocumentFileField
              value={fileReference}
              uploading={uploading}
              {...(errors.fileReference?.message ? { error: errors.fileReference.message } : {})}
              onUpload={async (file) => {
                const next = await onUpload(file);
                setValue("fileReference", next, { shouldDirty: true, shouldValidate: true });
              }}
              onClear={() =>
                setValue("fileReference", "", { shouldDirty: true, shouldValidate: true })
              }
            />

            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="size-4 rounded border-input"
                {...register("published")}
              />
              Опубликован
            </label>
          </div>

          <DialogFooter className="shrink-0">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Отмена
            </Button>
            <Button type="submit" loading={submitting || uploading}>
              {mode === "create" ? "Добавить" : "Сохранить"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
