import { useEffect, useRef, useState } from "react";
import { useLocation, useSearchParams } from "react-router";

import {
  fetchParticipant,
  type Participant,
  toAddParticipantRequest,
} from "@/entities/participant";
import { type DirectoryTeacher, fetchTeacher, toCreditTeacherRequest } from "@/entities/teacher";
import type {
  SetPerformanceRequest,
  SubmissionResource,
} from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";
import { useAutosave } from "@/shared/hooks";
import {
  Alert,
  Button,
  Divider,
  EmptyState,
  Input,
  LoadingState,
  Select,
  Textarea,
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
  needsAgeComposition,
  type PerformanceAxis,
  type PerformanceSelection,
  recommendedAgeCategoryId,
} from "../lib/admission";
import { CollectiveHeadcount, headcountMissing } from "./collective-headcount";
import { CollectiveMembers, isCollectiveEntry } from "./collective-members";
import { ParticipantPicker } from "./participant-picker";
import { TeacherPicker } from "./teacher-picker";
import { UploadControls } from "./upload-controls";

type NamedItem = { id: string; name: string; sortOrder: number };

/** Mirrors the backend bound on the performance comment. */
const COMMENT_MAX_LENGTH = 1000;

/** Mirrors the backend bound on the age composition. */
const AGE_COMPOSITION_MAX_LENGTH = 300;

/**
 * What to write in the age field, phrased around what the organizer will do with it.
 *
 * A mixed band is scored by reducing the group to one age, and which age that is
 * changes what matters in the answer — an average asks for everybody, the oldest asks
 * who the eldest is. Saying so up front beats a rejected entry later.
 */
function ageCompositionHint(method: string | null | undefined): string {
  const base =
    "Категория смешанная: укажите, участники какого возраста выходят на сцену — например, «12 детей 8–11 лет и 2 педагога 30+».";
  if (method === "AVERAGE") {
    return `${base} Организатор оценивает такую группу по среднему возрасту.`;
  }
  if (method === "OLDEST") {
    return `${base} Организатор оценивает такую группу по возрасту старшего участника.`;
  }
  if (method === "YOUNGEST") {
    return `${base} Организатор оценивает такую группу по возрасту младшего участника.`;
  }
  return base;
}

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
  const [comment, setComment] = useState(submission.performance?.comment ?? "");
  const [ageComposition, setAgeComposition] = useState(
    submission.performance?.ageComposition ?? "",
  );

  const setPerformance = useSetPerformance(submissionId);

  const setAxis = (axis: PerformanceAxis, value: string) => {
    setSelection((current) => clearDownstream({ ...current, [axis]: value }, axis));
  };

  // Only nominations whose registration window is currently open can be applied to;
  // a closed/not-yet-open nomination would be rejected by the backend on submit.
  const openNominations = registration.nominations.filter(
    (nomination) => nomination.registrationOpen,
  );
  const nominationOptions = options(openNominations, admissibleValues(rules, {}, "nominationId"));
  const noOpenNominations = openNominations.length === 0;
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

  const mixedAge = needsAgeComposition(registration.ageCategories, selection.ageCategoryId);
  const mixedMethod = registration.ageCategories.find(
    (band) => band.id === selection.ageCategoryId,
  )?.mixedCalculationMethod;

  const durationSeconds = (Number(minutes) || 0) * 60 + (Number(seconds) || 0);
  const admissible = isFullyAdmissible(rules, selection);
  const canSave = admissible && title.trim().length > 0 && durationSeconds > 0;

  // The note is offered only where the festival asks for one. Where it does not, the
  // field is absent *and* nothing is sent: the Applications context refuses to accept
  // a submission that still carries a comment, so a note written before the organizer
  // switched the field off would otherwise block a submission nobody can now fix.
  const commentEnabled = registration.participantCommentEnabled;
  const outgoingComment = commentEnabled ? comment.trim() : "";

  // Autosave: persist the performance whenever a complete, admissible combination
  // differs from what is stored. Seed the ref with the mounted (persisted) state so
  // an unchanged form never re-saves, and debounce so typing does not save per key.
  const signatureOf = (note: string): string | null =>
    canSave
      ? [
          title.trim(),
          durationSeconds,
          selection.nominationId,
          selection.disciplineId,
          selection.ageCategoryId,
          selection.participantGroupId,
          selection.participationFormatId,
          note,
          ageComposition.trim(),
        ].join("|")
      : null;
  const saveSignature = signatureOf(outgoingComment);
  // Seeded from the *stored* note rather than the outgoing one: with the field
  // switched off the two differ, and that difference is what makes the first autosave
  // clear a note left over from when the field was still on.
  const savedSignature = useRef<string | null>(
    signatureOf(submission.performance?.comment?.trim() ?? ""),
  );
  const { mutate: savePerformance } = setPerformance;
  // Flushed rather than dropped when the form goes away: collapsing this card, opening
  // another one or leaving the page used to clear the timer with the last seconds of
  // typing still in it, and the title came back the way the server remembered it.
  const { schedule } = useAutosave<{ payload: SetPerformanceRequest; signature: string }>(
    ({ payload, signature }) =>
      savePerformance(payload, {
        onSuccess: () => {
          savedSignature.current = signature;
        },
        onError: () => {
          toast.error("Не удалось сохранить выступление");
        },
      }),
  );
  useEffect(() => {
    if (!saveSignature || savedSignature.current === saveSignature) {
      return;
    }
    schedule({
      signature: saveSignature,
      payload: {
        title: title.trim(),
        durationSeconds,
        nominationId: selection.nominationId as string,
        disciplineId: selection.disciplineId as string,
        ageCategoryId: selection.ageCategoryId as string,
        participantGroupId: selection.participantGroupId as string,
        participationFormatId: selection.participationFormatId as string,
        comment: outgoingComment,
        // Sent whatever the category is: a value left over from a mixed band the
        // applicant has since switched away from is harmless, and dropping it would
        // lose what they wrote if they switch back.
        ageComposition: ageComposition.trim(),
      },
    });
  }, [saveSignature, schedule, title, durationSeconds, selection, outgoingComment, ageComposition]);

  return (
    <div className="flex flex-col gap-4">
      {noOpenNominations ? (
        <Alert variant="warning" title="Приём заявок закрыт">
          Сейчас нет жанров, открытых для регистрации. Проверьте сроки приёма заявок по жанрам.
        </Alert>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-2">
        <Select
          label="Жанр"
          placeholder="Выберите"
          options={nominationOptions}
          value={selection.nominationId ?? ""}
          onValueChange={(value: string) => setAxis("nominationId", value)}
        />
        <Select
          label="Номинация"
          placeholder="Выберите"
          disabled={!selection.nominationId}
          options={disciplineOptions}
          value={selection.disciplineId ?? ""}
          onValueChange={(value: string) => setAxis("disciplineId", value)}
        />
        <Select
          label="Состав участников"
          placeholder="Выберите"
          disabled={!selection.disciplineId}
          options={groupOptions}
          value={selection.participantGroupId ?? ""}
          onValueChange={(value: string) => setAxis("participantGroupId", value)}
        />
        <Select
          label="Возрастная категория"
          placeholder="Выберите"
          disabled={!selection.participantGroupId}
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
          label="Формат участия"
          placeholder="Выберите"
          disabled={!selection.ageCategoryId}
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

      {/* Смешанная возрастная категория намеренно не задаёт возраст: даты рождения в
          заявке описывают перечисленных людей, а не номер. Кто на сцене на самом деле —
          знает только тот, кто подаёт заявку, поэтому здесь он это и пишет. */}
      {mixedAge ? (
        <Textarea
          label="Возрастной состав участников"
          description={ageCompositionHint(mixedMethod)}
          required
          rows={2}
          value={ageComposition}
          maxLength={AGE_COMPOSITION_MAX_LENGTH}
          onChange={(event) => setAgeComposition(event.target.value)}
        />
      ) : null}

      {/* Shown only where the organizer accepts a note, and optional wherever it is
          shown: having something to say about the number is the exception. */}
      {commentEnabled ? (
        <Textarea
          label="Дополнительная информация для организаторов"
          description="Здесь можно указать особенности выступления: выход на сцену, реквизит, оборудование, особенности фонограммы и любую другую информацию, которая поможет организаторам."
          value={comment}
          // The backend bounds the note, so stop at the same length rather than let a
          // request fail: the field is a convenience, never a blocker on saving.
          maxLength={COMMENT_MAX_LENGTH}
          onChange={(event) => setComment(event.target.value)}
        />
      ) : null}

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
            : "Заполните жанр, название и длительность номера"}
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

      <AutoPricing submissionId={submissionId} submission={submission} />
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
  // The band counts people, not entries: a collective contributes its headcount.
  const count = submission.participants.reduce((total, p) => total + (p.memberCount ?? 1), 0);
  const bandLabel = group
    ? group.maxCount == null
      ? `${group.minCount}+`
      : `${group.minCount}–${group.maxCount}`
    : null;
  // A collective that has not stated its headcount counts as one person, which would
  // make the band warning shout about a number nobody has entered yet. Its own field
  // is already asking for it, so hold the warning until there is something to judge.
  const awaitingHeadcount = submission.participants.some(
    (p) => isCollectiveEntry(p) && headcountMissing(p),
  );
  const outOfBand =
    group != null &&
    count > 0 &&
    !awaitingHeadcount &&
    (count < group.minCount || (group.maxCount != null && count > group.maxCount));
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const handledPick = useRef<string | null>(null);

  // Attached without a headcount: a collective states it in its own field below,
  // where the applicant is looking at the entry rather than scrolling a registry.
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
      {/* Wraps rather than squeezes: the button's label cannot shrink, so on a narrow
          screen it belongs on its own line instead of half off the card. */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="min-w-0 text-sm font-medium">
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
          <div key={participant.id} className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm">
                {participant.displayName}
                {participant.birthDate ? ` · ${participant.birthDate}` : ""}
                {participant.memberCount > 1 ? ` · ${participant.memberCount} чел.` : ""}
              </span>
              <Button
                variant="outline"
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
            {/* A collective states its headcount here, once it is chosen — and only a
                collective can have a roster: a solo participant is already named on
                their own diploma. */}
            {isCollectiveEntry(participant) ? (
              <>
                <CollectiveHeadcount
                  submissionId={submissionId}
                  participant={participant}
                  bandLabel={bandLabel}
                />
                <CollectiveMembers submissionId={submissionId} participant={participant} />
              </>
            ) : null}
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
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="min-w-0 text-sm font-medium">Педагоги</p>
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
              variant="outline"
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

/**
 * Keeps the submission's price in step with the performance, and says what to make
 * of the absence of one.
 *
 * A priced performance carries its price as the badge on the card's header, so
 * nothing is repeated here. An unpriced one is not an error and not a blank to be
 * filled in: pricing is optional per combination, and where the festival set none
 * the regulation is what the applicant should go by — which is what this says, once
 * the combination is actually chosen and the backend has answered for it.
 */
function AutoPricing({
  submissionId,
  submission,
}: {
  submissionId: string;
  submission: SubmissionResource;
}): React.JSX.Element | null {
  const calculate = useCalculatePrice(submissionId);
  const { mutate } = calculate;
  const performance = submission.performance;
  const participantCount = submission.participants.reduce(
    (total, participant) => total + (participant.memberCount ?? 1),
    0,
  );

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
      // A combination the festival never priced simply stays unpriced.
      mutate();
    }
  }, [signature, mutate]);

  // Nothing to say until this exact combination has been quoted and came back without
  // a price: until then a missing price means "not asked yet", not "unpriced".
  const quoted = signature !== null && lastPriced.current === signature && !calculate.isPending;
  if (submission.price || !quoted) {
    return null;
  }

  return (
    <>
      <Divider />
      <p className="text-sm text-muted-foreground">Стоимость номера определяется положением.</p>
    </>
  );
}
