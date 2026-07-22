import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { applyProblemToForm } from "@/features/auth";
import type {
  AutosaveState,
  CompetitionSectionId,
  PublicationChecklist,
} from "@/features/competitions";
import {
  buildRegulationChangeLog,
  clearRegulationDraft,
  createEmptyRegulationDraft,
  detectRegulationSource,
  draftToAddRegulationPayload,
  findCurrentRegulation,
  loadRegulationChangeNotes,
  loadRegulationDraft,
  type RegulationDraftValues,
  type RegulationSourceType,
  regulationDraftSchema,
  rememberRegulationChangeNote,
  resolveMediaUrl,
  saveRegulationDraft,
  sortRegulationsNewestFirst,
  useAddRegulationMutation,
  useMakeRegulationCurrentMutation,
  useRemoveRegulationMutation,
  useUnsavedChangesGuard,
  useUploadRegulationFileMutation,
} from "@/features/competitions";
import type { _Regulation, CompetitionDetail } from "@/shared/api/generated/model-competitions";
import { toEmbeddableDocUrl } from "@/shared/lib";
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
  Input,
  PageSection,
  Tabs,
  TabsList,
  TabsTrigger,
  Textarea,
  toast,
} from "@/shared/ui";
import { PublicationChecklistPanel } from "@/widgets/competition-workspace/ui/publication-checklist-panel";
import { CurrentRegulationCard } from "./current-regulation-card";
import { PdfUploadField } from "./pdf-upload-field";
import { RegulationChangeLog } from "./regulation-change-log";
import { RegulationLinkField } from "./regulation-link-field";
import { RegulationVersionHistory } from "./regulation-version-history";

interface RegulationsSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

export function RegulationsSection({
  competition,
  checklist,
  onAutosaveStateChange,
  onNavigateSection,
}: RegulationsSectionProps): React.JSX.Element {
  const isReadOnly = competition.status === "COMPLETED";
  const addRegulation = useAddRegulationMutation();
  const uploadFile = useUploadRegulationFileMutation();
  const makeCurrent = useMakeRegulationCurrentMutation();
  const removeRegulation = useRemoveRegulationMutation();

  const regulations = useMemo(
    () => sortRegulationsNewestFirst(competition.regulations),
    [competition.regulations],
  );
  const current = useMemo(
    () => findCurrentRegulation(competition.regulations, competition.currentRegulationId),
    [competition.currentRegulationId, competition.regulations],
  );

  const storedDraft = loadRegulationDraft(competition.id);
  const [draftOpen, setDraftOpen] = useState(
    () => storedDraft != null || competition.regulations.length === 0,
  );
  const [publishOpen, setPublishOpen] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<_Regulation | null>(null);
  const [previewTarget, setPreviewTarget] = useState<_Regulation | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [changeNotes, setChangeNotes] = useState(() => loadRegulationChangeNotes(competition.id));
  const [sourceMode, setSourceMode] = useState<RegulationSourceType>(() =>
    detectRegulationSource(storedDraft?.fileReference),
  );

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    setError,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<RegulationDraftValues>({
    resolver: zodResolver(regulationDraftSchema),
    defaultValues: storedDraft ?? createEmptyRegulationDraft(competition.regulations, current),
    mode: "onBlur",
  });

  const watchedValues = watch();
  const unsavedGuard = useUnsavedChangesGuard(isDirty && draftOpen && !isReadOnly);

  useEffect(() => {
    if (isReadOnly || !draftOpen) {
      onAutosaveStateChange("idle");
      return;
    }
    onAutosaveStateChange(isDirty ? "dirty" : "idle");
  }, [draftOpen, isDirty, isReadOnly, onAutosaveStateChange]);

  useEffect(() => {
    if (!draftOpen || isReadOnly) {
      return;
    }
    saveRegulationDraft(competition.id, watchedValues);
  }, [competition.id, draftOpen, isReadOnly, watchedValues]);

  const changeLog = useMemo(
    () => buildRegulationChangeLog(regulations, changeNotes),
    [changeNotes, regulations],
  );

  const openDraft = (fromCurrent = true): void => {
    const next = createEmptyRegulationDraft(competition.regulations, fromCurrent ? current : null);
    const existing = loadRegulationDraft(competition.id);
    const values = existing ?? next;
    reset(values);
    setSourceMode(detectRegulationSource(values.fileReference));
    setDraftOpen(true);
    setFormError(null);
  };

  const discardDraft = (): void => {
    clearRegulationDraft(competition.id);
    reset(createEmptyRegulationDraft(competition.regulations, current));
    setSourceMode("file");
    setDraftOpen(competition.regulations.length === 0);
    setFormError(null);
    onAutosaveStateChange("idle");
  };

  // Switching source resets the reference so a PDF path is never submitted as a
  // link (or vice versa); each mode owns its own value.
  const changeSourceMode = (mode: RegulationSourceType): void => {
    if (mode === sourceMode) {
      return;
    }
    setSourceMode(mode);
    setValue("fileReference", "", { shouldDirty: true, shouldValidate: false });
  };

  const handlePdfUpload = async (file: File): Promise<void> => {
    const fileReference = await uploadFile.mutateAsync({
      competitionId: competition.id,
      file,
    });
    setValue("fileReference", fileReference, { shouldDirty: true, shouldValidate: true });
    toast.success("PDF загружен");
  };

  const onPublish = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await addRegulation.mutateAsync({
        competitionId: competition.id,
        payload: draftToAddRegulationPayload(values),
      });
      if (values.changeNote?.trim()) {
        rememberRegulationChangeNote(competition.id, values.version, values.changeNote);
        setChangeNotes(loadRegulationChangeNotes(competition.id));
      }
      clearRegulationDraft(competition.id);
      reset(createEmptyRegulationDraft([...competition.regulations], null));
      setDraftOpen(false);
      setPublishOpen(false);
      onAutosaveStateChange("saved");
      toast.success(`Версия ${values.version} опубликована`);
    } catch (error) {
      const message = applyProblemToForm<RegulationDraftValues>(error, {
        setError,
        knownFields: ["title", "version", "publicationDate", "fileReference", "changeNote"],
      });
      if (message) {
        setFormError(message);
      }
      toast.error("Не удалось опубликовать положение");
      setPublishOpen(false);
    }
  });

  const handleMakeCurrent = async (regulationId: string): Promise<void> => {
    try {
      await makeCurrent.mutateAsync({ competitionId: competition.id, regulationId });
      toast.success("Текущая версия обновлена");
    } catch {
      toast.error("Не удалось назначить текущую версию");
    }
  };

  const handleRemove = async (): Promise<void> => {
    if (!removeTarget) {
      return;
    }
    try {
      await removeRegulation.mutateAsync({
        competitionId: competition.id,
        regulationId: removeTarget.id,
      });
      toast.success(`Версия ${removeTarget.version} удалена`);
      setRemoveTarget(null);
    } catch {
      toast.error("Не удалось удалить версию");
    }
  };

  const draftPreviewUrl = toEmbeddableDocUrl(resolveMediaUrl(watchedValues.fileReference));
  const previewUrl = toEmbeddableDocUrl(
    resolveMediaUrl(previewTarget?.fileReference ?? watchedValues.fileReference),
  );

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="space-y-6">
          {isReadOnly ? (
            <Alert variant="warning" title="Фестиваль в архиве">
              Положение доступно только для просмотра.
            </Alert>
          ) : (
            <Alert variant="info" title="Неизменяемые версии">
              Опубликованную версию нельзя править. Загрузите PDF или укажите ссылку на документ
              (например, Google Документ). Ссылка остаётся неизменной, а сам документ можно
              редактировать в любой момент — участники всегда увидят актуальную версию.
            </Alert>
          )}

          <PageSection
            title="Положение фестиваля"
            description="Черновик готовится локально; публикация создаёт неизменяемую версию на сервере."
          >
            <CurrentRegulationCard
              regulation={current}
              isReadOnly={isReadOnly}
              onCreateDraft={() => openDraft(true)}
            />
          </PageSection>

          {draftOpen && !isReadOnly ? (
            <PageSection
              title="Черновик новой версии"
              description="Заполните метаданные, загрузите PDF или укажите ссылку и опубликуйте. До публикации черновик хранится в этой сессии."
            >
              <Card className="shadow-none">
                <CardHeader className="pb-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <CardTitle className="text-base">Параметры версии</CardTitle>
                    <Badge variant="warning">Черновик</Badge>
                  </div>
                  <CardDescription>
                    После публикации эта версия станет текущей и появится в истории.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {formError ? (
                    <Alert variant="danger" title="Не удалось опубликовать">
                      {formError}
                    </Alert>
                  ) : null}

                  <div className="grid gap-4 md:grid-cols-2">
                    <Input
                      label="Название"
                      required
                      error={errors.title?.message}
                      {...register("title")}
                    />
                    <Input
                      label="Версия"
                      required
                      error={errors.version?.message}
                      {...register("version")}
                    />
                    <Input
                      label="Дата публикации"
                      type="date"
                      required
                      error={errors.publicationDate?.message}
                      {...register("publicationDate")}
                    />
                    <div className="md:col-span-2">
                      <Textarea
                        label="Описание изменений"
                        description="Необязательно. Сохранится в журнале на этом устройстве."
                        rows={3}
                        error={errors.changeNote?.message}
                        {...register("changeNote")}
                      />
                    </div>
                  </div>

                  <div className="space-y-3">
                    <Tabs
                      value={sourceMode}
                      onValueChange={(value) => changeSourceMode(value as RegulationSourceType)}
                    >
                      <TabsList>
                        <TabsTrigger value="file">PDF-файл</TabsTrigger>
                        <TabsTrigger value="link">Ссылка на документ</TabsTrigger>
                      </TabsList>
                    </Tabs>

                    {sourceMode === "file" ? (
                      <PdfUploadField
                        value={watchedValues.fileReference}
                        uploading={uploadFile.isPending}
                        {...(errors.fileReference?.message
                          ? { error: errors.fileReference.message }
                          : {})}
                        onUpload={handlePdfUpload}
                        onClear={() =>
                          setValue("fileReference", "", { shouldDirty: true, shouldValidate: true })
                        }
                      />
                    ) : (
                      <RegulationLinkField
                        value={watchedValues.fileReference}
                        {...(errors.fileReference?.message
                          ? { error: errors.fileReference.message }
                          : {})}
                        onChange={(value) =>
                          setValue("fileReference", value, {
                            shouldDirty: true,
                            shouldValidate: true,
                          })
                        }
                      />
                    )}
                  </div>

                  {draftPreviewUrl ? (
                    <div className="overflow-hidden rounded-md border border-border">
                      <iframe
                        title="Превью черновика положения"
                        src={draftPreviewUrl}
                        className="h-72 w-full bg-background"
                      />
                    </div>
                  ) : null}

                  <div className="flex flex-wrap justify-end gap-2">
                    {competition.regulations.length > 0 ? (
                      <Button type="button" variant="outline" onClick={discardDraft}>
                        Отменить черновик
                      </Button>
                    ) : null}
                    <Button
                      type="button"
                      loading={isSubmitting || addRegulation.isPending}
                      onClick={() => setPublishOpen(true)}
                    >
                      Опубликовать версию
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </PageSection>
          ) : null}

          <PageSection title="Версии" description="Управление опубликованными документами.">
            <RegulationVersionHistory
              regulations={regulations}
              isReadOnly={isReadOnly}
              makingCurrentId={
                makeCurrent.isPending ? (makeCurrent.variables?.regulationId ?? null) : null
              }
              removingId={
                removeRegulation.isPending
                  ? (removeRegulation.variables?.regulationId ?? null)
                  : null
              }
              onMakeCurrent={(id) => void handleMakeCurrent(id)}
              onRemove={(id) => {
                const target = regulations.find((item) => item.id === id) ?? null;
                setRemoveTarget(target);
              }}
              onPreview={setPreviewTarget}
            />
          </PageSection>
        </div>

        <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
          <RegulationChangeLog entries={changeLog} />
          <Card className="shadow-none">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Как это работает</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-muted-foreground text-sm">
              <p>1. Создайте черновик: загрузите PDF или вставьте ссылку на документ.</p>
              <p>2. Опубликуйте — версия станет текущей и неизменяемой.</p>
              <p>
                3. Ссылку менять не нужно — правьте сам документ. Для смены файла опубликуйте новую
                версию.
              </p>
            </CardContent>
          </Card>
          <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
        </aside>
      </div>

      <Dialog open={publishOpen} onOpenChange={setPublishOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Опубликовать версию {watchedValues.version}?</DialogTitle>
            <DialogDescription>
              После публикации документ нельзя изменить. Новая версия станет текущей для фестиваля.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setPublishOpen(false)}>
              Отмена
            </Button>
            <Button
              type="button"
              loading={isSubmitting || addRegulation.isPending}
              onClick={() => void onPublish()}
            >
              Опубликовать
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={removeTarget != null}
        onOpenChange={(open) => {
          if (!open) {
            setRemoveTarget(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Удалить версию {removeTarget?.version}?</DialogTitle>
            <DialogDescription>
              Версия будет удалена из истории. Если это текущая версия, текущей станет последняя
              оставшаяся.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setRemoveTarget(null)}>
              Отмена
            </Button>
            <Button
              type="button"
              variant="danger"
              loading={removeRegulation.isPending}
              onClick={() => void handleRemove()}
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
            <DialogTitle>
              Превью: {previewTarget?.title} (v{previewTarget?.version})
            </DialogTitle>
          </DialogHeader>
          {previewUrl ? (
            <iframe
              title="Превью выбранной версии положения"
              src={previewUrl}
              className="h-[70vh] w-full rounded-md border border-border bg-background"
            />
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog
        open={unsavedGuard.isBlocked}
        onOpenChange={(open) => {
          if (!open) {
            unsavedGuard.reset();
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Уйти без сохранения черновика?</DialogTitle>
            <DialogDescription>
              Черновик положения ещё не опубликован. Можно остаться и продолжить или уйти — черновик
              останется в сессии браузера.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => unsavedGuard.reset()}>
              Остаться
            </Button>
            <Button variant="danger" onClick={() => unsavedGuard.proceed()}>
              Уйти
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
