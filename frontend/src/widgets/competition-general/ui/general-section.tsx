import { zodResolver } from "@hookform/resolvers/zod";
import { Check } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { applyProblemToForm } from "@/features/auth";
import type {
  AutosaveState,
  CompetitionSectionId,
  PublicationChecklist,
} from "@/features/competitions";
import {
  brandingValuesToPayload,
  competitionStatusLabel,
  competitionToGeneralValues,
  contactSyncTargets,
  type GeneralInformationValues,
  generalFormSnapshot,
  generalInformationSchema,
  generalValuesToPayload,
  useSyncContactMutation,
  useUnsavedChangesGuard,
  useUpdateBrandingMutation,
  useUpdateGeneralInformationMutation,
  useUploadPosterMutation,
} from "@/features/competitions";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import {
  Alert,
  Button,
  Card,
  CardContent,
  DatePicker,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Input,
  PageSection,
  Textarea,
  toast,
} from "@/shared/ui";
import { PublicationChecklistPanel } from "@/widgets/competition-workspace/ui/publication-checklist-panel";
import { GeneralLivePreview } from "./general-live-preview";
import { PosterUploadField } from "./poster-upload-field";
import { VenueSection } from "./venue-section";

interface GeneralSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

const AUTOSAVE_DELAY_MS = 1200;

export function GeneralSection({
  competition,
  checklist,
  onAutosaveStateChange,
  onNavigateSection,
}: GeneralSectionProps): React.JSX.Element {
  const updateGeneral = useUpdateGeneralInformationMutation();
  const updateBranding = useUpdateBrandingMutation();
  const uploadPoster = useUploadPosterMutation();
  const syncContact = useSyncContactMutation();
  const [formError, setFormError] = useState<string | null>(null);
  const [justSaved, setJustSaved] = useState(false);
  const justSavedTimer = useRef<number | null>(null);

  const autosaveTimer = useRef<number | null>(null);
  const lastSavedSnapshot = useRef(generalFormSnapshot(competitionToGeneralValues(competition)));
  const lastSyncedVersion = useRef(competition.version);
  const saveGeneration = useRef(0);
  const isDirtyRef = useRef(false);
  const isSavingRef = useRef(false);

  const {
    register,
    control,
    handleSubmit,
    reset,
    watch,
    getValues,
    setValue,
    setError,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<GeneralInformationValues>({
    resolver: zodResolver(generalInformationSchema),
    defaultValues: competitionToGeneralValues(competition),
    mode: "onBlur",
  });

  isDirtyRef.current = isDirty;
  const watchedValues = watch();
  const unsavedGuard = useUnsavedChangesGuard(isDirty);

  useEffect(() => {
    if (isSavingRef.current || isDirtyRef.current) {
      return;
    }
    if (competition.version === lastSyncedVersion.current) {
      return;
    }

    const values = competitionToGeneralValues(competition);
    reset(values);
    lastSavedSnapshot.current = generalFormSnapshot(values);
    lastSyncedVersion.current = competition.version;
    onAutosaveStateChange("idle");
  }, [competition, onAutosaveStateChange, reset]);

  const flashSavedFeedback = useCallback(() => {
    setJustSaved(true);
    if (justSavedTimer.current != null) {
      window.clearTimeout(justSavedTimer.current);
    }
    justSavedTimer.current = window.setTimeout(() => {
      setJustSaved(false);
      justSavedTimer.current = null;
    }, 2000);
  }, []);

  useEffect(() => {
    return () => {
      if (justSavedTimer.current != null) {
        window.clearTimeout(justSavedTimer.current);
      }
    };
  }, []);

  const persist = useCallback(
    async (values: GeneralInformationValues, mode: "autosave" | "manual") => {
      const snapshot = generalFormSnapshot(values);
      if (snapshot === lastSavedSnapshot.current) {
        onAutosaveStateChange("saved");
        if (mode === "manual") {
          flashSavedFeedback();
          toast.success("Сохранено");
        }
        return;
      }

      const generation = ++saveGeneration.current;
      const baselineVersion = competition.version;
      setFormError(null);
      isSavingRef.current = true;
      onAutosaveStateChange("saving");

      try {
        await updateGeneral.mutateAsync({
          competitionId: competition.id,
          payload: generalValuesToPayload(values),
        });
        const afterBranding = await updateBranding.mutateAsync({
          competitionId: competition.id,
          payload: brandingValuesToPayload(values),
        });

        if (afterBranding.version < baselineVersion) {
          onAutosaveStateChange("error");
          setFormError(
            "На сервере есть более новая версия фестиваля. Обновите страницу и попробуйте снова.",
          );
          toast.error("Не удалось сохранить — на сервере более новые данные");
          return;
        }

        for (const target of contactSyncTargets(afterBranding, values)) {
          const previous = afterBranding.contacts.find(
            (contact) => contact.type === target.contactType,
          );
          const previousValue = previous?.value ?? "";
          if (target.value.trim() === previousValue.trim()) {
            continue;
          }
          await syncContact.mutateAsync({
            competitionId: competition.id,
            contactType: target.contactType,
            value: target.value,
            ...(target.existingContactId ? { existingContactId: target.existingContactId } : {}),
          });
        }

        if (generation !== saveGeneration.current) {
          return;
        }

        lastSavedSnapshot.current = snapshot;
        lastSyncedVersion.current = Math.max(afterBranding.version, competition.version);
        reset(values);
        onAutosaveStateChange("saved");
        if (mode === "manual") {
          flashSavedFeedback();
          toast.success("Сохранено");
        }
      } catch (error) {
        if (generation !== saveGeneration.current) {
          return;
        }
        onAutosaveStateChange("error");
        const message = applyProblemToForm<GeneralInformationValues>(error, {
          setError,
          knownFields: [
            "title",
            "season",
            "description",
            "poster",
            "venueName",
            "venueAddress",
            "vk",
            "instagram",
            "telegram",
          ],
        });
        if (message) {
          setFormError(message);
        }
        toast.error(
          mode === "manual" ? "Не удалось сохранить фестиваль" : "Автосохранение не удалось",
        );
        throw error;
      } finally {
        if (generation === saveGeneration.current) {
          isSavingRef.current = false;
        }
      }
    },
    [
      competition.id,
      competition.version,
      flashSavedFeedback,
      onAutosaveStateChange,
      reset,
      setError,
      syncContact,
      updateBranding,
      updateGeneral,
    ],
  );

  useEffect(() => {
    const clearTimer = (): void => {
      if (autosaveTimer.current != null) {
        window.clearTimeout(autosaveTimer.current);
        autosaveTimer.current = null;
      }
    };

    const scheduleAutosave = (): void => {
      clearTimer();
      autosaveTimer.current = window.setTimeout(() => {
        void handleSubmit(async (nextValues) => {
          try {
            await persist(nextValues, "autosave");
          } catch {
            // Error state is handled inside persist.
          }
        })();
      }, AUTOSAVE_DELAY_MS);
    };

    if (!isDirty) {
      clearTimer();
      if (!isSavingRef.current) {
        onAutosaveStateChange(
          generalFormSnapshot(getValues()) === lastSavedSnapshot.current ? "idle" : "dirty",
        );
      }
      return clearTimer;
    }

    onAutosaveStateChange("dirty");
    scheduleAutosave();

    const subscription = watch(() => {
      onAutosaveStateChange("dirty");
      scheduleAutosave();
    });

    return () => {
      subscription.unsubscribe();
      clearTimer();
    };
  }, [getValues, handleSubmit, isDirty, onAutosaveStateChange, persist, watch]);

  const onSubmit = handleSubmit(async (nextValues) => {
    await persist(nextValues, "manual");
  });

  const handlePosterUpload = async (file: File): Promise<void> => {
    const detail = await uploadPoster.mutateAsync({
      competitionId: competition.id,
      file,
    });
    const poster = detail.branding.poster ?? "";
    setValue("poster", poster, { shouldDirty: false, shouldValidate: true });
    const nextValues = { ...getValues(), poster };
    lastSavedSnapshot.current = generalFormSnapshot(nextValues);
    lastSyncedVersion.current = detail.version;
    reset(nextValues);
    onAutosaveStateChange("saved");
    toast.success("Афиша загружена");
  };

  const handlePosterClear = (): void => {
    setValue("poster", "", { shouldDirty: true, shouldValidate: true });
    onAutosaveStateChange("dirty");
  };

  const isReadOnly = competition.status === "COMPLETED";

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <form onSubmit={onSubmit} noValidate className="space-y-6">
          {formError ? (
            <Alert variant="danger" title="Не удалось сохранить изменения">
              {formError}
            </Alert>
          ) : null}

          {isReadOnly ? (
            <Alert variant="warning" title="Фестиваль в архиве">
              Этот фестиваль доступен только для просмотра. Перед редактированием его нужно вывести
              из архива.
            </Alert>
          ) : null}

          <PageSection
            title="Основная информация"
            description="Ключевые данные для рабочего пространства организатора и публичных страниц."
          >
            <Card className="shadow-none">
              <CardContent className="grid gap-4 pt-6 md:grid-cols-2">
                <Input
                  label="Название фестиваля"
                  required
                  error={errors.title?.message}
                  disabled={isReadOnly}
                  {...register("title")}
                />
                <Input
                  label="Сезон"
                  required
                  error={errors.season?.message}
                  disabled={isReadOnly}
                  {...register("season")}
                />
                <div className="md:col-span-2">
                  <Textarea
                    label="Краткое описание"
                    rows={4}
                    error={errors.description?.message}
                    disabled={isReadOnly}
                    {...register("description")}
                  />
                </div>
              </CardContent>
            </Card>
          </PageSection>

          <PageSection
            title="Брендинг"
            description="Афиша фестиваля для карточек и публичных страниц."
          >
            <Card className="shadow-none">
              <CardContent className="pt-6">
                <PosterUploadField
                  value={watchedValues.poster ?? ""}
                  disabled={isReadOnly}
                  uploading={uploadPoster.isPending}
                  {...(errors.poster?.message ? { error: errors.poster.message } : {})}
                  onUpload={handlePosterUpload}
                  onClear={handlePosterClear}
                />
              </CardContent>
            </Card>
          </PageSection>

          {/* Only the festival's own dates: the registration window that matters is the
              one set per genre in «Жанры», so there is no announcement period here to
              contradict it. */}
          <PageSection title="Даты фестиваля" description="Когда проходит фестиваль.">
            <Card className="shadow-none">
              <CardContent className="grid gap-4 pt-6 md:grid-cols-2">
                <Controller
                  control={control}
                  name="competitionStart"
                  render={({ field }) => (
                    <DatePicker
                      label="Начало фестиваля"
                      value={field.value ?? ""}
                      onChange={field.onChange}
                      disabled={isReadOnly}
                      {...(errors.competitionStart?.message != null
                        ? { error: errors.competitionStart.message }
                        : {})}
                    />
                  )}
                />
                <Controller
                  control={control}
                  name="competitionEnd"
                  render={({ field }) => (
                    <DatePicker
                      label="Окончание фестиваля"
                      value={field.value ?? ""}
                      onChange={field.onChange}
                      disabled={isReadOnly}
                      {...(errors.competitionEnd?.message != null
                        ? { error: errors.competitionEnd.message }
                        : {})}
                    />
                  )}
                />
              </CardContent>
            </Card>
          </PageSection>

          <VenueSection
            competition={competition}
            isReadOnly={isReadOnly}
            nameField={register("venueName")}
            addressField={register("venueAddress")}
            nameError={errors.venueName?.message}
            addressError={errors.venueAddress?.message}
            onAutosaveStateChange={onAutosaveStateChange}
          />

          <PageSection title="Онлайн-присутствие" description="Ссылки на социальные сети.">
            <Card className="shadow-none">
              <CardContent className="grid gap-4 pt-6 md:grid-cols-2">
                <Input
                  label="ВКонтакте"
                  error={errors.vk?.message}
                  disabled={isReadOnly}
                  {...register("vk")}
                />
                <Input
                  label="Instagram"
                  error={errors.instagram?.message}
                  disabled={isReadOnly}
                  {...register("instagram")}
                />
                <Input
                  label="Telegram"
                  error={errors.telegram?.message}
                  disabled={isReadOnly}
                  {...register("telegram")}
                />
              </CardContent>
            </Card>
          </PageSection>

          {!isReadOnly ? (
            <div className="flex justify-end">
              <Button
                type="submit"
                loading={isSubmitting}
                variant={justSaved ? "success" : "primary"}
                leftIcon={justSaved ? <Check aria-hidden="true" /> : undefined}
              >
                {justSaved ? "Сохранено" : "Сохранить"}
              </Button>
            </div>
          ) : null}
        </form>

        <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
          <GeneralLivePreview
            values={watchedValues}
            statusLabel={competitionStatusLabel(competition.status)}
          />
          <PublicationChecklistPanel checklist={checklist} onNavigateSection={onNavigateSection} />
        </aside>
      </div>

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
            <DialogTitle>Отменить несохранённые изменения?</DialogTitle>
            <DialogDescription>
              На странице «Общее» есть несохранённые правки. Уйти без сохранения или продолжить
              редактирование.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => unsavedGuard.reset()}>
              Продолжить редактирование
            </Button>
            <Button variant="danger" onClick={() => unsavedGuard.proceed()}>
              Отменить изменения
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
