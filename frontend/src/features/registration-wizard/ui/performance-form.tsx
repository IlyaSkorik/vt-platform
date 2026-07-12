import { useState } from "react";

import type { SubmissionResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";
import { Alert, Badge, Button, Divider, Input, LoadingState, Select } from "@/shared/ui";

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

      <div>
        <Button
          size="sm"
          disabled={!canSave}
          loading={setPerformance.isPending}
          onClick={() =>
            setPerformance.mutate({
              title: title.trim(),
              durationSeconds,
              nominationId: selection.nominationId as string,
              disciplineId: selection.disciplineId as string,
              ageCategoryId: selection.ageCategoryId as string,
              participantGroupId: selection.participantGroupId as string,
              participationFormatId: selection.participationFormatId as string,
            })
          }
        >
          Сохранить номер
        </Button>
      </div>

      <Divider />
      <ParticipantsSection submissionId={submissionId} submission={submission} />

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
      <PriceSection
        submissionId={submissionId}
        submission={submission}
        canPrice={submission.performance != null}
      />
    </div>
  );
}

function ParticipantsSection({
  submissionId,
  submission,
}: {
  submissionId: string;
  submission: SubmissionResource;
}): React.JSX.Element {
  const add = useAddParticipant(submissionId);
  const remove = useRemoveParticipant(submissionId);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [gender, setGender] = useState("FEMALE");

  const reset = () => {
    setFirstName("");
    setLastName("");
    setBirthDate("");
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm font-medium">Участники</p>
      {submission.participants.map((participant) => (
        <div key={participant.id} className="flex items-center justify-between gap-2">
          <span className="text-sm">
            {participant.lastName} {participant.firstName} · {participant.birthDate}
          </span>
          <Button
            variant="ghost"
            size="xs"
            loading={remove.isPending}
            onClick={() => remove.mutate(participant.id)}
          >
            Удалить
          </Button>
        </div>
      ))}
      <div className="grid items-end gap-2 sm:grid-cols-4">
        <Input
          label="Имя"
          value={firstName}
          onChange={(event) => setFirstName(event.target.value)}
        />
        <Input
          label="Фамилия"
          value={lastName}
          onChange={(event) => setLastName(event.target.value)}
        />
        <Input
          label="Дата рождения"
          type="date"
          value={birthDate}
          onChange={(event) => setBirthDate(event.target.value)}
        />
        <Select
          label="Пол"
          options={[
            { value: "FEMALE", label: "Жен." },
            { value: "MALE", label: "Муж." },
          ]}
          value={gender}
          onValueChange={setGender}
        />
      </div>
      <div>
        <Button
          variant="outline"
          size="sm"
          disabled={!firstName.trim() || !lastName.trim() || !birthDate}
          loading={add.isPending}
          onClick={() =>
            add.mutate(
              {
                firstName: firstName.trim(),
                lastName: lastName.trim(),
                birthDate,
                gender: gender as "MALE" | "FEMALE",
              },
              { onSuccess: reset },
            )
          }
        >
          Добавить участника
        </Button>
      </div>
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
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [role, setRole] = useState("");

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm font-medium">Педагоги</p>
      {submission.teachers.map((teacher) => (
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
      ))}
      <div className="grid items-end gap-2 sm:grid-cols-3">
        <Input
          label="Имя"
          value={firstName}
          onChange={(event) => setFirstName(event.target.value)}
        />
        <Input
          label="Фамилия"
          value={lastName}
          onChange={(event) => setLastName(event.target.value)}
        />
        <Input label="Роль" value={role} onChange={(event) => setRole(event.target.value)} />
      </div>
      <div>
        <Button
          variant="outline"
          size="sm"
          disabled={!firstName.trim() || !lastName.trim() || !role.trim()}
          loading={add.isPending}
          onClick={() =>
            add.mutate(
              { firstName: firstName.trim(), lastName: lastName.trim(), role: role.trim() },
              {
                onSuccess: () => {
                  setFirstName("");
                  setLastName("");
                  setRole("");
                },
              },
            )
          }
        >
          Добавить педагога
        </Button>
      </div>
    </div>
  );
}

function PriceSection({
  submissionId,
  submission,
  canPrice,
}: {
  submissionId: string;
  submission: SubmissionResource;
  canPrice: boolean;
}): React.JSX.Element {
  const calculate = useCalculatePrice(submissionId);
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="text-sm">
        Стоимость номера:{" "}
        {submission.price ? (
          <Badge variant="success">
            {submission.price.amount} {submission.price.currency}
          </Badge>
        ) : (
          <span className="text-muted-foreground">не рассчитана</span>
        )}
      </div>
      <Button
        variant="secondary"
        size="sm"
        disabled={!canPrice}
        loading={calculate.isPending}
        onClick={() => calculate.mutate()}
      >
        Рассчитать стоимость
      </Button>
    </div>
  );
}
