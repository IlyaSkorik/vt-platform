import { Download, Eye, FileText, GripVertical, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import type {
  AutosaveState,
  CompetitionSectionId,
  DocumentFormValues,
  DocumentListSort,
  PublicationChecklist,
} from "@/features/competitions";
import {
  buildReorderedSortUpdates,
  createEmptyDocumentForm,
  DOCUMENT_CATEGORY_LABELS,
  DOCUMENT_LIST_SORT_OPTIONS,
  DOCUMENT_VISIBILITY_LABELS,
  documentFormToAddPayload,
  documentFormToUpdatePayload,
  documentToFormValues,
  documentUploadDate,
  filterAndSortDocuments,
  formatDateTime,
  isPreviewableDocument,
  nextDocumentSortOrder,
  resolveMediaUrl,
  useAddDocumentMutation,
  useRemoveDocumentMutation,
  useReorderDocumentsMutation,
  useSetDocumentPublishedMutation,
  useUpdateDocumentMutation,
  useUploadDocumentFileMutation,
} from "@/features/competitions";
import type { _Document, CompetitionDetail } from "@/shared/api/generated/model-competitions";
import { cn } from "@/shared/lib";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  IconButton,
  Input,
  PageSection,
  Select,
  toast,
} from "@/shared/ui";
import { PublicationChecklistPanel } from "@/widgets/competition-workspace/ui/publication-checklist-panel";
import { DocumentFormDialog } from "./document-form-dialog";
import { DocumentsSkeleton } from "./documents-skeleton";

interface DocumentsSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function DocumentsSection({
  competition,
  checklist,
  isLoading = false,
  onAutosaveStateChange,
  onNavigateSection,
}: DocumentsSectionProps): React.JSX.Element {
  const isReadOnly = competition.status === "COMPLETED";
  const uploadFile = useUploadDocumentFileMutation();
  const addDocument = useAddDocumentMutation();
  const updateDocument = useUpdateDocumentMutation();
  const removeDocument = useRemoveDocumentMutation();
  const setPublished = useSetDocumentPublishedMutation();
  const reorderDocuments = useReorderDocumentsMutation();

  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<DocumentListSort>("manual");
  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "edit">("create");
  const [editingDocument, setEditingDocument] = useState<_Document | null>(null);
  const [formValues, setFormValues] = useState<DocumentFormValues>(createEmptyDocumentForm());
  const [deleteTarget, setDeleteTarget] = useState<_Document | null>(null);
  const [previewTarget, setPreviewTarget] = useState<_Document | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [sectionError, setSectionError] = useState<string | null>(null);

  const documents = competition.documents;
  const visibleDocuments = useMemo(
    () => filterAndSortDocuments(documents, search, sort),
    [documents, search, sort],
  );

  const previewUrl = resolveMediaUrl(previewTarget?.fileReference);
  const previewKind = previewTarget ? isPreviewableDocument(previewTarget.fileReference) : null;

  if (isLoading) {
    return <DocumentsSkeleton />;
  }

  const openCreate = (): void => {
    setFormMode("create");
    setEditingDocument(null);
    setFormValues(createEmptyDocumentForm(nextDocumentSortOrder(documents)));
    setFormOpen(true);
  };

  const openEdit = (document: _Document): void => {
    setFormMode("edit");
    setEditingDocument(document);
    setFormValues(documentToFormValues(document));
    setFormOpen(true);
  };

  const handleUpload = async (file: File): Promise<string> => {
    const fileReference = await uploadFile.mutateAsync({
      competitionId: competition.id,
      file,
    });
    toast.success("Файл загружен");
    return fileReference;
  };

  const handleSubmit = async (values: DocumentFormValues): Promise<void> => {
    setSectionError(null);
    onAutosaveStateChange("saving");
    try {
      if (formMode === "create") {
        await addDocument.mutateAsync({
          competitionId: competition.id,
          payload: documentFormToAddPayload(values),
        });
        toast.success("Документ добавлен");
      } else if (editingDocument) {
        await updateDocument.mutateAsync({
          competitionId: competition.id,
          documentId: editingDocument.id,
          payload: documentFormToUpdatePayload(values),
        });
        if (values.published !== editingDocument.published) {
          await setPublished.mutateAsync({
            competitionId: competition.id,
            documentId: editingDocument.id,
            published: values.published,
          });
        }
        toast.success("Документ сохранён");
      }
      setFormOpen(false);
      onAutosaveStateChange("saved");
    } catch {
      setSectionError("Не удалось сохранить документ.");
      onAutosaveStateChange("error");
      toast.error("Не удалось сохранить документ");
    }
  };

  const handleDelete = async (): Promise<void> => {
    if (!deleteTarget) {
      return;
    }
    setSectionError(null);
    try {
      await removeDocument.mutateAsync({
        competitionId: competition.id,
        documentId: deleteTarget.id,
      });
      toast.success("Документ удалён");
      setDeleteTarget(null);
    } catch {
      setSectionError("Не удалось удалить документ.");
      toast.error("Не удалось удалить документ");
    }
  };

  const handleReorder = async (fromId: string, toId: string): Promise<void> => {
    if (isReadOnly || sort !== "manual" || fromId === toId) {
      return;
    }
    const ordered = filterAndSortDocuments(documents, "", "manual").map((item) => item.id);
    const fromIndex = ordered.indexOf(fromId);
    const toIndex = ordered.indexOf(toId);
    if (fromIndex < 0 || toIndex < 0) {
      return;
    }
    const next = [...ordered];
    const [moved] = next.splice(fromIndex, 1);
    if (!moved) {
      return;
    }
    next.splice(toIndex, 0, moved);

    const updates = buildReorderedSortUpdates(next, documents).map((item) => ({
      documentId: item.documentId,
      payload: item.values,
    }));
    if (updates.length === 0) {
      return;
    }

    onAutosaveStateChange("saving");
    try {
      await reorderDocuments.mutateAsync({
        competitionId: competition.id,
        updates,
      });
      onAutosaveStateChange("saved");
      toast.success("Порядок обновлён");
    } catch {
      onAutosaveStateChange("error");
      toast.error("Не удалось изменить порядок");
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {isReadOnly ? (
            <Alert variant="warning" title="Фестиваль в архиве">
              Документы доступны только для просмотра.
            </Alert>
          ) : null}

          {sectionError ? (
            <Alert variant="danger" title="Ошибка">
              {sectionError}
            </Alert>
          ) : null}

          <PageSection
            title="Документы фестиваля"
            description="Загружайте файлы для участников и публичных страниц. Порядок можно менять перетаскиванием."
          >
            <Card className="shadow-none">
              <CardHeader className="gap-4 pb-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle className="text-base">Библиотека файлов</CardTitle>
                    <CardDescription>
                      {documents.length === 0
                        ? "Пока нет загруженных документов."
                        : `Всего документов: ${documents.length}`}
                    </CardDescription>
                  </div>
                  {!isReadOnly ? (
                    <Button type="button" onClick={openCreate}>
                      <Plus className="size-4" aria-hidden="true" />
                      Добавить документ
                    </Button>
                  ) : null}
                </div>

                <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_14rem]">
                  <Input
                    label="Поиск"
                    placeholder="Название или описание"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    leadingIcon={<Search aria-hidden="true" />}
                  />
                  <Select
                    label="Сортировка"
                    value={sort}
                    onValueChange={(value) => setSort(value as DocumentListSort)}
                    options={DOCUMENT_LIST_SORT_OPTIONS.map((option) => ({
                      value: option.value,
                      label: option.label,
                    }))}
                  />
                </div>
              </CardHeader>

              <CardContent className="space-y-3">
                {visibleDocuments.length === 0 ? (
                  <EmptyState
                    title={documents.length === 0 ? "Документов пока нет" : "Ничего не найдено"}
                    description={
                      documents.length === 0
                        ? "Загрузите первый файл — программу, расписание или памятку."
                        : "Измените поисковый запрос или сбросьте фильтр."
                    }
                    action={
                      !isReadOnly && documents.length === 0 ? (
                        <Button type="button" onClick={openCreate}>
                          Загрузить документ
                        </Button>
                      ) : undefined
                    }
                  />
                ) : (
                  <ul className="space-y-3" aria-label="Список документов фестиваля">
                    {visibleDocuments.map((document) => {
                      const fileUrl = resolveMediaUrl(document.fileReference);
                      const uploadedAt = documentUploadDate(document);
                      const canPreview = isPreviewableDocument(document.fileReference) != null;
                      return (
                        <li
                          key={document.id}
                          draggable={!isReadOnly && sort === "manual"}
                          onDragStart={() => setDraggedId(document.id)}
                          onDragEnd={() => setDraggedId(null)}
                          onDragOver={(event) => {
                            if (!isReadOnly && sort === "manual") {
                              event.preventDefault();
                            }
                          }}
                          onDrop={(event) => {
                            event.preventDefault();
                            if (draggedId) {
                              void handleReorder(draggedId, document.id);
                            }
                            setDraggedId(null);
                          }}
                          className={cn(
                            "rounded-md border border-border bg-background px-3 py-3",
                            draggedId === document.id && "opacity-60",
                          )}
                        >
                          <div className="flex flex-wrap items-start gap-3">
                            {!isReadOnly && sort === "manual" ? (
                              <span
                                className="mt-1 cursor-grab text-muted-foreground active:cursor-grabbing"
                                aria-hidden="true"
                                title="Перетащите для изменения порядка"
                              >
                                <GripVertical className="size-4" />
                              </span>
                            ) : null}

                            <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                              <FileText className="size-4" aria-hidden="true" />
                            </div>

                            <div className="min-w-0 flex-1 space-y-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="font-medium text-sm">{document.title}</p>
                                <Badge variant="outline" size="sm">
                                  {DOCUMENT_CATEGORY_LABELS[
                                    document.category as keyof typeof DOCUMENT_CATEGORY_LABELS
                                  ] ?? document.category}
                                </Badge>
                                <Badge variant="secondary" size="sm">
                                  {DOCUMENT_VISIBILITY_LABELS[
                                    document.visibility as keyof typeof DOCUMENT_VISIBILITY_LABELS
                                  ] ?? document.visibility}
                                </Badge>
                                {document.published ? (
                                  <Badge variant="success" size="sm">
                                    Опубликован
                                  </Badge>
                                ) : (
                                  <Badge variant="neutral" size="sm">
                                    Черновик
                                  </Badge>
                                )}
                              </div>
                              {document.description ? (
                                <p className="text-muted-foreground text-sm">
                                  {document.description}
                                </p>
                              ) : null}
                              <p className="text-muted-foreground text-xs">
                                Порядок: {document.sortOrder}
                                {" · "}
                                Загружен:{" "}
                                {uploadedAt ? formatDateTime(uploadedAt.toISOString()) : "—"}
                              </p>
                            </div>

                            <div className="flex flex-wrap gap-2">
                              {canPreview ? (
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="outline"
                                  onClick={() => setPreviewTarget(document)}
                                >
                                  <Eye className="size-3.5" aria-hidden="true" />
                                  Превью
                                </Button>
                              ) : null}
                              {fileUrl ? (
                                <Button asChild size="sm" variant="outline">
                                  <a href={fileUrl} download target="_blank" rel="noreferrer">
                                    <Download className="size-3.5" aria-hidden="true" />
                                    Скачать
                                  </a>
                                </Button>
                              ) : null}
                              {!isReadOnly ? (
                                <>
                                  <IconButton
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    aria-label="Редактировать документ"
                                    icon={<Pencil aria-hidden="true" />}
                                    onClick={() => openEdit(document)}
                                  />
                                  <IconButton
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    aria-label="Удалить документ"
                                    icon={<Trash2 aria-hidden="true" />}
                                    onClick={() => setDeleteTarget(document)}
                                  />
                                </>
                              ) : null}
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </CardContent>
            </Card>
          </PageSection>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
          <Card className="shadow-none">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Как работать с документами</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-muted-foreground text-sm">
              <p>1. Добавьте файл через кнопку или drag-and-drop в форме.</p>
              <p>2. Укажите название, описание и видимость.</p>
              <p>3. В режиме «Ручной порядок» перетаскивайте карточки для сортировки.</p>
            </CardContent>
          </Card>
          <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
        </aside>
      </div>

      <DocumentFormDialog
        open={formOpen}
        mode={formMode}
        initialValues={formValues}
        uploading={uploadFile.isPending}
        submitting={addDocument.isPending || updateDocument.isPending || setPublished.isPending}
        onOpenChange={setFormOpen}
        onUpload={handleUpload}
        onSubmit={handleSubmit}
      />

      <Dialog
        open={deleteTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setDeleteTarget(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Удалить документ?</DialogTitle>
            <DialogDescription>
              «{deleteTarget?.title}» будет удалён из фестиваля. Файл останется в хранилище, но
              ссылка из фестиваля исчезнет.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDeleteTarget(null)}>
              Отмена
            </Button>
            <Button
              type="button"
              variant="danger"
              loading={removeDocument.isPending}
              onClick={() => void handleDelete()}
            >
              Удалить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={previewTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setPreviewTarget(null);
          }
        }}
      >
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{previewTarget?.title}</DialogTitle>
            <DialogDescription>Превью загруженного файла.</DialogDescription>
          </DialogHeader>
          {previewUrl && previewKind === "pdf" ? (
            <iframe
              title={`Превью ${previewTarget?.title ?? "документа"}`}
              src={previewUrl}
              className="h-[70vh] w-full rounded-md border border-border bg-background"
            />
          ) : null}
          {previewUrl && previewKind === "image" ? (
            <img
              src={previewUrl}
              alt={previewTarget?.title ?? "Документ"}
              className="max-h-[70vh] w-full rounded-md object-contain"
            />
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
