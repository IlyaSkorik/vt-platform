import { useEffect, useRef, useState } from "react";
import { useLocation, useSearchParams } from "react-router";

import {
  fetchParticipant,
  type Participant,
  toAddParticipantRequest,
} from "@/entities/participant";
import { type DirectoryTeacher, fetchTeacher, toCreditTeacherRequest } from "@/entities/teacher";
import type { SubmissionResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";
import {
  Alert,
  Badge,
  Button,
  Divider,
  EmptyState,
  Input,
  LoadingState,
  Select,
  toast,
} from "@/shared/ui";

import {
  useAddParticipant,
  useAddTeacher,
  useCalculatePrice,
  useRemoveParticipant,
  useRemoveTeacher,
  useSetPerformance,
  useSubmission,
} from "../api/hooks";
import {
  admissibleValues,
  clearDownstream,
  isFullyAdmissible,
  type PerformanceAxis,
  type PerformanceSelection,
  recommendedAgeCategoryId,
} from "../lib/admission";
import { ParticipantPicker } from "./participant-picker";
import { TeacherPicker } from "./teacher-picker";
import { UploadControls } from "./upload-controls";

type NamedItem = { id: string; name: string; sortOrder: number };

function options(
  items: readonly NamedItem[],
  allowed: Set<string>,
): { value: string; label: string }[] {
  return items
    .filter((item) => allowed.has(item.id))
    .sort((a, b) => a.sortOrder - b.sortOrder)
    .map((item) => ({ value: item.id, label: item.name }));
}

function selectionFromSubmission(submission: SubmissionResource): PerformanceSelection {
  const performance = submission.performance;
  if (!performance) {
    return {};
  }
  return {
    nominationId: performance.nominationId,
    disciplineId: performance.disciplineId,
    ageCategoryId: performance.ageCategoryId,
    participantGroupId: performance.participantGroupId,
    participationFormatId: performance.participationFormatId,
  };
}

export function PerformanceForm({
  submissionId,
  registration,
}: {
  submissionId: string;
  registration: Registration;
}): React.JSX.Element {
  const { data: submission, isLoading } = useSubmission(submissionId);
  if (isLoading || !submission) {
    return <LoadingState label="Загружаем выступление…" size="sm" />;
  }
  return (
    <PerformanceFormInner
      key={submissionId}
      submissionId={submissionId}
      submission={submission}
      registration={registration}
    />
  );
}

function PerformanceFormInner({
  submissionId,
  submission,
  registration,
}: {
  submissionId: string;
  submission: SubmissionResource;
  registration: Registration;
}): React.JSX.Element {
  const rules = registration.admissionRules;
  const [selection, setSelection] = useState<PerformanceSelection>(() =>
    selectionFromSubmission(submission),
  );
  const [title, setTitle] = useState(submission.performance?.title ?? "");
  const [minutes, setMinutes] = useState(() =>
    String(Math.floor((submission.performance?.durationSeconds ?? 0) / 60) || ""),
  );
  const [seconds, setSeconds] = useState(() =>
    String((submission.performance?.durationSeconds ?? 0) % 60 || ""),
  );

  const setPerformance = useSetPerformance(submissionId);

  const setAxis = (axis: PerformanceAxis, value: string) => {
    setSelection((current) => clearDownstream({ ...current, [axis]: value }, axis));
  };

  const nominationOptions = options(
    registration.nominations,
    admissibleValues(rules, {}, "nominationId"),
  );
  const disciplineOptions = options(
    registration.disciplines,
    admissibleValues(rules, selection, "disciplineId"),
  );
  const ageOptions = registration.ageCategories.filter((band) =>
    admissibleValues(rules, selection, "ageCategoryId").has(band.id),
  );
  const groupOptions = options(
    registration.participantGroups,
    admissibleValues(rules, selection, "participantGroupId"),
  );
  const formatOptions = options(
    registration.participationFormats,
    admissibleValues(rules, selection, "participationFormatId"),
  );

  const leadBirthDate = submission.participants[0]?.birthDate ?? "";
  const recommendedAge = recommendedAgeCategoryId(
    ageOptions.map((band) => ({ id: band.id, minAge: band.minAge, maxAge: band.maxAge })),
    leadBirthDate,
    new Date(),
  );

  const durationSeconds = (Number(minutes) || 0) * 60 + (Number(seconds) || 0);
  const admissible = isFullyAdmissible(rules, selection);
  const canSave = admissible && title.trim().length > 0 && durationSeconds > 0;

  // Autosave: persist the performance whenever a complete, admissible combination
  // differs from what is stored. Seed the ref with the mounted (persisted) state so
  // an unchanged form never re-saves, and debounce so typing does not save per key.
  const saveSignature = canSave
    ? [
        title.trim(),
        durationSeconds,
        selection.nominationId,
        selection.disciplineId,
        selection.ageCategoryId,
        selection.participantGroupId,
        selection.participationFormatId,
      ].join("|")
    : null;
  const savedSignature = useRef<string | null>(saveSignature);
  const { mutate: savePerformance } = setPerformance;
  useEffect(() => {
    if (!saveSignature || savedSignature.current === saveSignature) {
      return;
    }
    const handle = setTimeout(() => {
      savedSignature.current = saveSignature;
      savePerformance({
        title: title.trim(),
        durationSeconds,
        nominationId: selection.nominationId as string,
        disciplineId: selection.disciplineId as string,
        ageCategoryId: selection.ageCategoryId as string,
        participantGroupId: selection.participantGroupId as string,
        participationFormatId: selection.participationFormatId as string,
      });
    }, 700);
    return () => clearTimeout(handle);
  }, [saveSignature, savePerformance, title, durationSeconds, selection]);

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <Select
          label="Номинация"
          placeholder="Выберите"
          options={nominationOptions}
          value={selection.nominationId ?? ""}
          onValueChange={(value: string) => setAxis("nominationId", value)}
        />
        <Select
          label="Дисциплина"
          placeholder="Выберите"
          disabled={!selection.nominationId}
          options={disciplineOptions}
          value={selection.disciplineId ?? ""}
          onValueChange={(value: string) => setAxis("disciplineId", value)}
        />
        <Select
          label="Возрастная категория"
          placeholder="Выберите"
          disabled={!selection.disciplineId}
          description={
            recommendedAge && recommendedAge !== selection.ageCategoryId
              ? `Рекомендуется по дате рождения: ${ageOptions.find((band) => band.id === recommendedAge)?.name ?? ""}`
              : undefined
          }
          options={ageOptions
            .slice()
            .sort((a, b) => a.sortOrder - b.sortOrder)
            .map((band) => ({ value: band.id, label: band.name }))}
          value={selection.ageCategoryId ?? ""}
          onValueChange={(value: string) => setAxis("ageCategoryId", value)}
        />
        <Select
          label="Состав участников"
          placeholder="Выберите"
          disabled={!selection.ageCategoryId}
          options={groupOptions}
          value={selection.participantGroupId ?? ""}
          onValueChange={(value: string) => setAxis("participantGroupId", value)}
        />
        <Select
          label="Формат участия"
          placeholder="Выберите"
          disabled={!selection.participantGroupId}
          options={formatOptions}
          value={selection.participationFormatId ?? ""}
          onValueChange={(value: string) => setAxis("participationFormatId", value)}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          label="Название номера"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <div className="flex items-end gap-2">
          <Input
            label="Мин."
            type="number"
            min={0}
            value={minutes}
            onChange={(event) => setMinutes(event.target.value)}
          />
          <Input
            label="Сек."
            type="number"
            min={0}
            max={59}
            value={seconds}
            onChange={(event) => setSeconds(event.target.value)}
          />
        </div>
      </div>

      {!admissible && Object.keys(selection).length > 0 ? (
        <Alert variant="info">
          Выберите допустимую комбинацию — доступны только сочетания, разрешённые фестивалем.
        </Alert>
      ) : null}

      <p className="text-xs text-muted-foreground">
        {setPerformance.isPending
          ? "Сохранение…"
          : canSave
            ? "Изменения сохраняются автоматически"
            : "Заполните номинацию, название и длительность номера"}
      </p>

      <Divider />
      <ParticipantsSection
        submissionId={submissionId}
        submission={submission}
        group={registration.participantGroups.find((g) => g.id === selection.participantGroupId)}
      />

      <Divider />
      <TeachersSection submissionId={submissionId} submission={submission} />

      <Divider />
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium">Файлы</p>
        <UploadControls
          submissionId={submissionId}
          submission={submission}
          requirement={registration.uploadRequirements.find(
            (requirement) => requirement.participationFormatId === selection.participationFormatId,
          )}
        />
      </div>

      <Divider />
      <PriceSection submissionId={submissionId} submission={submission} />
    </div>
  );
}

function ParticipantsSection({
  submissionId,
  submission,
  group,
}: {
  submissionId: string;
  submission: SubmissionResource;
  group: Registration["participantGroups"][number] | undefined;
}): React.JSX.Element {
  const add = useAddParticipant(submissionId);
  const remove = useRemoveParticipant(submissionId);
  const [pickerOpen, setPickerOpen] = useState(false);
  const count = submission.participants.length;
  const bandLabel = group
    ? group.maxCount == null
      ? `${group.minCount}+`
      : `${group.minCount}–${group.maxCount}`
    : null;
  const outOfBand =
    group != null &&
    count > 0 &&
    (count < group.minCount || (group.maxCount != null && count > group.maxCount));
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const handledPick = useRef<string | null>(null);

  const attach = (participant: Participant) => {
    add.mutate(toAddParticipantRequest(participant), {
      onSuccess: () => setPickerOpen(false),
      onError: () => toast.error("Не удалось добавить участника"),
    });
  };

  // Returning from "create participant" (the reusable registry page): the new
  // participant's id arrives as a query param — attach it to this performance and
  // clear the param so it is handled exactly once.
  useEffect(() => {
    const pickedId = searchParams.get("pickedParticipantId");
    const forSubmission = searchParams.get("submissionId");
    if (!pickedId || forSubmission !== submissionId || handledPick.current === pickedId) {
      return;
    }
    handledPick.current = pickedId;
    void fetchParticipant(pickedId)
      .then((participant) => add.mutateAsync(toAddParticipantRequest(participant)))
      .catch(() => toast.error("Не удалось добавить созданного участника"))
      .finally(() => {
        setSearchParams(
          (params) => {
            params.delete("pickedParticipantId");
            params.delete("submissionId");
            return params;
          },
          { replace: true },
        );
      });
  }, [searchParams, setSearchParams, submissionId, add]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium">
          Участники
          {bandLabel ? (
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              (состав: {bandLabel})
            </span>
          ) : null}
        </p>
        <Button variant="outline" size="sm" onClick={() => setPickerOpen(true)}>
          Выбрать участника
        </Button>
      </div>

      {outOfBand && group ? (
        <Alert variant="warning">
          Для выбранного состава требуется {bandLabel} участник(ов); сейчас выбрано {count}.
        </Alert>
      ) : null}

      {submission.participants.length === 0 ? (
        <EmptyState
          title="Участник не выбран"
          description="Выберите участника из вашего реестра — его данные подставятся автоматически."
        />
      ) : (
        submission.participants.map((participant) => (
          <div key={participant.id} className="flex items-center justify-between gap-2">
            <span className="text-sm">
              {participant.displayName}
              {participant.birthDate ? ` · ${participant.birthDate}` : ""}
            </span>
            <Button
              variant="ghost"
              size="xs"
              loading={remove.isPending}
              onClick={() =>
                remove.mutate(participant.id, {
                  onError: () => toast.error("Не удалось удалить участника"),
                })
              }
            >
              Удалить
            </Button>
          </div>
        ))
      )}

      <ParticipantPicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        onSelect={attach}
        submissionId={submissionId}
        returnTo={location.pathname}
        isAttaching={add.isPending}
      />
    </div>
  );
}

function TeachersSection({
  submissionId,
  submission,
}: {
  submissionId: string;
  submission: SubmissionResource;
}): React.JSX.Element {
  const add = useAddTeacher(submissionId);
  const remove = useRemoveTeacher(submissionId);
  const [pickerOpen, setPickerOpen] = useState(false);
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const handledPick = useRef<string | null>(null);

  const credit = (teacher: DirectoryTeacher) => {
    add.mutate(toCreditTeacherRequest(teacher), {
      onSuccess: () => setPickerOpen(false),
      onError: () => toast.error("Не удалось добавить педагога"),
    });
  };

  // Returning from "create teacher" (the reusable directory page): the new
  // teacher's id arrives as a query param — credit it to this performance and clear
  // the param so it is handled exactly once.
  useEffect(() => {
    const pickedId = searchParams.get("pickedTeacherId");
    const forSubmission = searchParams.get("submissionId");
    if (!pickedId || forSubmission !== submissionId || handledPick.current === pickedId) {
      return;
    }
    handledPick.current = pickedId;
    void fetchTeacher(pickedId)
      .then((teacher) => add.mutateAsync(toCreditTeacherRequest(teacher)))
      .catch(() => toast.error("Не удалось добавить созданного педагога"))
      .finally(() => {
        setSearchParams(
          (params) => {
            params.delete("pickedTeacherId");
            params.delete("submissionId");
            return params;
          },
          { replace: true },
        );
      });
  }, [searchParams, setSearchParams, submissionId, add]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium">Педагоги</p>
        <Button variant="outline" size="sm" onClick={() => setPickerOpen(true)}>
          Выбрать педагога
        </Button>
      </div>

      {submission.teachers.length === 0 ? (
        <EmptyState
          title="Педагог не выбран"
          description="Выберите педагога из вашего справочника — его данные подставятся автоматически."
        />
      ) : (
        submission.teachers.map((teacher) => (
          <div key={teacher.id} className="flex items-center justify-between gap-2">
            <span className="text-sm">
              {teacher.lastName} {teacher.firstName} · {teacher.role}
            </span>
            <Button
              variant="ghost"
              size="xs"
              loading={remove.isPending}
              onClick={() => remove.mutate(teacher.id)}
            >
              Удалить
            </Button>
          </div>
        ))
      )}

      <TeacherPicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        onSelect={credit}
        submissionId={submissionId}
        returnTo={location.pathname}
        isCrediting={add.isPending}
      />
    </div>
  );
}

function PriceSection({
  submissionId,
  submission,
}: {
  submissionId: string;
  submission: SubmissionResource;
}): React.JSX.Element {
  const calculate = useCalculatePrice(submissionId);
  const { mutate } = calculate;
  const performance = submission.performance;
  const participantCount = submission.participants.length;

  // The price is computed by the backend from the performance combination and the
  // participant count. Recalculate automatically whenever those change, so the
  // total stays live without a manual "calculate" step.
  const signature =
    performance && participantCount > 0
      ? [
          performance.nominationId,
          performance.disciplineId,
          performance.ageCategoryId,
          performance.participantGroupId,
          performance.participationFormatId,
          participantCount,
        ].join("|")
      : null;
  const lastPriced = useRef<string | null>(null);

  useEffect(() => {
    if (signature && lastPriced.current !== signature) {
      lastPriced.current = signature;
      // A combination with no configured price simply leaves the total blank.
      mutate();
    }
  }, [signature, mutate]);

  return (
    <div className="text-sm">
      Стоимость номера:{" "}
      {calculate.isPending ? (
        <span className="text-muted-foreground">рассчитывается…</span>
      ) : submission.price ? (
        <Badge variant="success">
          {submission.price.amount} {submission.price.currency}
        </Badge>
      ) : (
        <span className="text-muted-foreground">—</span>
      )}
    </div>
  );
}
