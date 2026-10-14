/**
 * Форма, которой организатор правит заявку за участника.
 *
 * Открывается из карточки номера и показывает ровно то, что в заявке лежит, — той
 * же структурой: солист хранит части ФИО, коллектив — название и численность.
 * Поэтому и переключатель «солист/коллектив» здесь есть: заявку заполняли руками,
 * и «Ансамбль „Радуга“», вписанный в поле фамилии, — обычная ошибка, ради которой
 * форму и открыли.
 *
 * Отправляется всё содержимое номера одним сохранением, а не по кнопке на поле:
 * организатор правит карточку целиком и хочет один раз нажать «Сохранить». Что
 * именно изменилось, считает сервер — он же об этом и пишет участнику.
 */
import { Plus, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

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

import {
  type CorrectablePerformance,
  type CorrectionPayload,
  correctionOrganization,
  type SubmissionTaxonomy,
  useCorrectSubmission,
} from "../api/hooks";

/** Одна строка формы участников. Локальная — в заявке такой формы нет. */
type PerformerDraft = {
  /** Идентификатор записи в заявке; пустой у только что добавленной. */
  id: string;
  /** Коллектив не имеет ФИО и даты рождения, солист — названия и численности. */
  collective: boolean;
  displayName: string;
  firstName: string;
  lastName: string;
  middleName: string;
  birthDate: string;
  gender: string;
  memberCount: string;
  /** Состав коллектива — по имени в строке: так его и вносят, копируя из списка. */
  members: string;
  /** Учреждение в поле — открывается тем, что печатается сейчас. */
  organization: string;
  /** Что в заявке закреплено и что из неё печатается — чтобы знать, правили ли поле. */
  pinnedOrganization: string | null;
  resolvedOrganization: string | null;
};

type TeacherDraft = {
  id: string;
  firstName: string;
  lastName: string;
  middleName: string;
  role: string;
};

const GENDERS = [
  { value: "FEMALE", label: "женский" },
  { value: "MALE", label: "мужской" },
  { value: "OTHER", label: "другой" },
];

/** Значение «не выбрано» для Radix: пустую строку он считает отсутствием выбора. */
const UNSET = "__unset__";

function performerDrafts(performance: CorrectablePerformance): PerformerDraft[] {
  return (performance.participants ?? []).map((performer) => {
    const collective = !performer.lastName || !performer.firstName;
    return {
      id: performer.id,
      collective,
      displayName: performer.displayName ?? "",
      firstName: performer.firstName ?? "",
      lastName: performer.lastName ?? "",
      middleName: performer.middleName ?? "",
      birthDate: performer.birthDate ?? "",
      gender: performer.gender ?? "",
      memberCount: String(performer.memberCount ?? 1),
      members: (performer.members ?? []).join("\n"),
      // Поле открыто на том, что печатается, а не на том, что закреплено: пустая
      // строка там, где учреждение на самом деле есть, читается как «его нет» —
      // и первое же сохранение сделало бы это правдой.
      organization: performer.resolvedOrganizationName ?? "",
      pinnedOrganization: performer.organizationName ?? null,
      resolvedOrganization: performer.resolvedOrganizationName ?? null,
    };
  });
}

function teacherDrafts(performance: CorrectablePerformance): TeacherDraft[] {
  return (performance.teachers ?? []).map((teacher) => ({
    id: teacher.id,
    firstName: teacher.firstName ?? "",
    lastName: teacher.lastName ?? "",
    middleName: teacher.middleName ?? "",
    role: teacher.role ?? "",
  }));
}

function options(rows: Array<{ id: string; name: string }>) {
  return rows.map((row) => ({ value: row.id, label: row.name }));
}

/**
 * «Учреждение» — единственное поле этой формы, которое правит не саму заявку.
 *
 * Школа участника лежит не в заявке, а в реестре участников кабинета заявителя, и
 * оттуда её читают все, кто её печатает: рабочая карточка, программа, протокол,
 * диплом. Здесь она правится **для бумаг этого фестиваля**: заполненное поле
 * закрепляется в самой заявке и перекрывает реестр для этого выступающего, не трогая
 * ни кабинет заявителя, ни его другие заявки, ни прошлые фестивали.
 *
 * Поэтому и подпись такая: пустое поле — не «учреждения нет», а «берём из реестра».
 * Это же и ответ на вопрос, что будет с уже поданными заявками: у них поле пусто,
 * они продолжают следовать за реестром, и появление этого поля их не изменило.
 */
function OrganizationField({
  row,
  index,
  onPatch,
}: {
  row: PerformerDraft;
  index: number;
  onPatch: (index: number, patch: Partial<PerformerDraft>) => void;
}): React.JSX.Element {
  return (
    <Input
      label="Учреждение"
      placeholder="Школа, студия, центр"
      description={
        row.pinnedOrganization
          ? "Исправлено для этой заявки. Очистите поле, чтобы снова брать из реестра участника."
          : "Берётся из реестра участника. Впишите другое — и в этой заявке будет печататься оно."
      }
      value={row.organization}
      onChange={(e) => onPatch(index, { organization: e.target.value })}
    />
  );
}

export type SubmissionCorrectionDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  performance: CorrectablePerformance;
  taxonomy: SubmissionTaxonomy;
  /** Что сервер посчитал изменённым — карточке, чтобы подтвердить правку одной строкой. */
  onSaved?: (changes: string[]) => void;
};

export function SubmissionCorrectionDialog({
  open,
  onOpenChange,
  performance,
  taxonomy,
  onSaved,
}: SubmissionCorrectionDialogProps): React.JSX.Element {
  const [title, setTitle] = useState("");
  const [minutes, setMinutes] = useState("0");
  const [seconds, setSeconds] = useState("0");
  const [nominationId, setNominationId] = useState("");
  const [disciplineId, setDisciplineId] = useState("");
  const [participantGroupId, setParticipantGroupId] = useState("");
  const [ageCategoryId, setAgeCategoryId] = useState("");
  const [participationFormatId, setParticipationFormatId] = useState("");
  const [performanceComment, setPerformanceComment] = useState("");
  const [ageComposition, setAgeComposition] = useState("");
  const [performers, setPerformers] = useState<PerformerDraft[]>([]);
  const [teachers, setTeachers] = useState<TeacherDraft[]>([]);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const correction = useCorrectSubmission();

  // Форма наполняется при каждом открытии, а не один раз при монтировании: карточку
  // перечитывают каждые десять секунд, и открытая заново форма должна показывать то,
  // что в заявке сейчас, а не то, что было при первом открытии.
  useEffect(() => {
    if (!open) return;
    const total = performance.durationSeconds ?? 0;
    setTitle(performance.title === "Без названия номера" ? "" : performance.title);
    setMinutes(String(Math.floor(total / 60)));
    setSeconds(String(total % 60));
    setNominationId(performance.nominationId ?? "");
    setDisciplineId(performance.disciplineId ?? "");
    setParticipantGroupId(performance.participantGroupId ?? "");
    setAgeCategoryId(performance.ageCategoryId ?? "");
    setParticipationFormatId(performance.participationFormatId ?? "");
    setPerformanceComment(performance.comment ?? "");
    setAgeComposition(performance.ageComposition ?? "");
    setPerformers(performerDrafts(performance));
    setTeachers(teacherDrafts(performance));
    setReason("");
    setError(null);
  }, [open, performance]);

  // Номинации показываются только от выбранного жанра, возрастные категории — только
  // от выбранного состава: справочник так и заведён, и предложить чужую строку значит
  // предложить сочетание, которого фестиваль не принимает.
  const disciplines = useMemo(
    () => taxonomy.disciplines.filter((row) => row.nominationId === nominationId),
    [taxonomy.disciplines, nominationId],
  );
  const ageCategories = useMemo(
    () => taxonomy.ageCategories.filter((row) => row.participantGroupId === participantGroupId),
    [taxonomy.ageCategories, participantGroupId],
  );

  const patchPerformer = (index: number, patch: Partial<PerformerDraft>) => {
    setPerformers((previous) =>
      previous.map((row, position) => (position === index ? { ...row, ...patch } : row)),
    );
  };
  const patchTeacher = (index: number, patch: Partial<TeacherDraft>) => {
    setTeachers((previous) =>
      previous.map((row, position) => (position === index ? { ...row, ...patch } : row)),
    );
  };

  const save = () => {
    setError(null);
    const durationSeconds =
      Math.max(0, Number(minutes) || 0) * 60 + Math.max(0, Number(seconds) || 0);
    if (!title.trim()) {
      setError("Укажите название номера.");
      return;
    }
    if (
      !nominationId ||
      !disciplineId ||
      !participantGroupId ||
      !ageCategoryId ||
      !participationFormatId
    ) {
      setError("Заполните жанр, номинацию, состав, возрастную категорию и форму участия.");
      return;
    }
    if (performers.length === 0) {
      setError("В номере должен остаться хотя бы один участник.");
      return;
    }
    const brokenPerformer = performers.find((row) =>
      row.collective ? !row.displayName.trim() : !row.lastName.trim() || !row.firstName.trim(),
    );
    if (brokenPerformer) {
      setError("У каждого участника нужны фамилия и имя, у коллектива — название.");
      return;
    }
    const brokenTeacher = teachers.find(
      (row) => !row.lastName.trim() || !row.firstName.trim() || !row.role.trim(),
    );
    if (brokenTeacher) {
      setError("У каждого педагога нужны фамилия, имя и роль.");
      return;
    }

    const payload: CorrectionPayload = {
      performance: {
        title: title.trim(),
        durationSeconds,
        nominationId,
        disciplineId,
        ageCategoryId,
        participantGroupId,
        participationFormatId,
        comment: performanceComment.trim(),
        ageComposition: ageComposition.trim(),
      },
      participants: performers.map((row) => ({
        ...(row.id ? { id: row.id } : {}),
        // Солисту подпись не передаём: сервер соберёт её из ФИО, и исправленная
        // фамилия попадёт в неё сама. Коллектив подписью и живёт.
        displayName: row.collective ? row.displayName.trim() : null,
        firstName: row.collective ? null : row.firstName.trim(),
        lastName: row.collective ? null : row.lastName.trim(),
        middleName: row.collective ? null : row.middleName.trim() || null,
        birthDate: row.collective ? null : row.birthDate || null,
        gender: row.collective ? null : row.gender || null,
        memberCount: row.collective ? Math.max(1, Number(row.memberCount) || 1) : 1,
        members: row.collective
          ? row.members
              .split("\n")
              .map((name) => name.trim())
              .filter(Boolean)
          : [],
        organizationName: correctionOrganization(row.organization, {
          organizationName: row.pinnedOrganization,
          resolvedOrganizationName: row.resolvedOrganization,
        }),
      })),
      teachers: teachers.map((row) => ({
        ...(row.id ? { id: row.id } : {}),
        firstName: row.firstName.trim(),
        lastName: row.lastName.trim(),
        middleName: row.middleName.trim() || null,
        role: row.role.trim(),
      })),
      comment: reason.trim(),
    };

    correction.mutate(
      { submissionId: performance.submissionId, payload },
      {
        onSuccess: (result) => {
          onSaved?.(result.changes);
          onOpenChange(false);
        },
        onError: (mutationError) => {
          setError(
            mutationError instanceof Error
              ? mutationError.message
              : "Не удалось сохранить исправление.",
          );
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Исправить заявку за участника</DialogTitle>
          <DialogDescription>
            Правка попадёт в историю заявки, а участник получит письмо со списком изменений.
            Стоимость участия не пересчитывается.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <section aria-label="Выступление" className="space-y-3">
            <p className="text-sm font-medium">Выступление</p>
            <Input
              label="Название номера"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Минут"
                type="number"
                min={0}
                value={minutes}
                onChange={(e) => setMinutes(e.target.value)}
              />
              <Input
                label="Секунд"
                type="number"
                min={0}
                max={59}
                value={seconds}
                onChange={(e) => setSeconds(e.target.value)}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Select
                label="Жанр"
                placeholder="Выберите жанр"
                value={nominationId || UNSET}
                onValueChange={(value) => {
                  setNominationId(value === UNSET ? "" : value);
                  // Номинация принадлежит жанру: оставить прежнюю значит оставить
                  // сочетание, которого в справочнике нет.
                  setDisciplineId("");
                }}
                options={options(taxonomy.nominations)}
              />
              <Select
                label="Номинация"
                placeholder="Выберите номинацию"
                value={disciplineId || UNSET}
                onValueChange={(value) => setDisciplineId(value === UNSET ? "" : value)}
                options={options(disciplines)}
              />
              <Select
                label="Состав"
                placeholder="Выберите состав"
                value={participantGroupId || UNSET}
                onValueChange={(value) => {
                  setParticipantGroupId(value === UNSET ? "" : value);
                  setAgeCategoryId("");
                }}
                options={options(taxonomy.participantGroups)}
              />
              <Select
                label="Возрастная категория"
                placeholder="Выберите категорию"
                value={ageCategoryId || UNSET}
                onValueChange={(value) => setAgeCategoryId(value === UNSET ? "" : value)}
                options={options(ageCategories)}
              />
              <Select
                label="Форма участия"
                placeholder="Выберите форму"
                value={participationFormatId || UNSET}
                onValueChange={(value) => setParticipationFormatId(value === UNSET ? "" : value)}
                options={options(taxonomy.participationFormats)}
              />
              <Input
                label="Возрастной состав"
                description="Заполняется для смешанной категории"
                value={ageComposition}
                onChange={(e) => setAgeComposition(e.target.value)}
              />
            </div>
            <Textarea
              value={performanceComment}
              onChange={(e) => setPerformanceComment(e.target.value)}
              placeholder="Дополнительная информация о номере"
            />
          </section>

          <section aria-label="Участники" className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Участники</p>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  setPerformers((previous) => [
                    ...previous,
                    {
                      id: "",
                      collective: false,
                      displayName: "",
                      firstName: "",
                      lastName: "",
                      middleName: "",
                      birthDate: "",
                      gender: "",
                      memberCount: "1",
                      members: "",
                      organization: "",
                      pinnedOrganization: null,
                      resolvedOrganization: null,
                    },
                  ])
                }
              >
                <Plus className="size-4" /> Добавить
              </Button>
            </div>
            {performers.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                Участников нет — добавьте хотя бы одного.
              </p>
            ) : null}
            {performers.map((row, index) => (
              <div key={row.id || `new-${index}`} className="space-y-3 rounded-md border p-3">
                <div className="flex items-center justify-between gap-2">
                  <Select
                    value={row.collective ? "collective" : "solo"}
                    onValueChange={(value) =>
                      patchPerformer(index, { collective: value === "collective" })
                    }
                    options={[
                      { value: "solo", label: "Солист" },
                      { value: "collective", label: "Коллектив" },
                    ]}
                    size="sm"
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      setPerformers((previous) =>
                        previous.filter((_, position) => position !== index),
                      )
                    }
                  >
                    <Trash2 className="size-4" /> Убрать
                  </Button>
                </div>
                {row.collective ? (
                  <div className="space-y-3">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Input
                        label="Название коллектива"
                        value={row.displayName}
                        onChange={(e) => patchPerformer(index, { displayName: e.target.value })}
                      />
                      <Input
                        label="Численность"
                        type="number"
                        min={1}
                        value={row.memberCount}
                        onChange={(e) => patchPerformer(index, { memberCount: e.target.value })}
                      />
                    </div>
                    <Textarea
                      value={row.members}
                      onChange={(e) => patchPerformer(index, { members: e.target.value })}
                      placeholder="Состав коллектива — по одному ФИО в строке (нужен для именных дипломов)"
                    />
                    <OrganizationField row={row} index={index} onPatch={patchPerformer} />
                  </div>
                ) : (
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Input
                      label="Фамилия"
                      value={row.lastName}
                      onChange={(e) => patchPerformer(index, { lastName: e.target.value })}
                    />
                    <Input
                      label="Имя"
                      value={row.firstName}
                      onChange={(e) => patchPerformer(index, { firstName: e.target.value })}
                    />
                    <Input
                      label="Отчество"
                      value={row.middleName}
                      onChange={(e) => patchPerformer(index, { middleName: e.target.value })}
                    />
                    <Input
                      label="Дата рождения"
                      type="date"
                      value={row.birthDate}
                      onChange={(e) => patchPerformer(index, { birthDate: e.target.value })}
                    />
                    <Select
                      label="Пол"
                      placeholder="Не указан"
                      value={row.gender || UNSET}
                      onValueChange={(value) =>
                        patchPerformer(index, { gender: value === UNSET ? "" : value })
                      }
                      options={GENDERS}
                    />
                    <OrganizationField row={row} index={index} onPatch={patchPerformer} />
                  </div>
                )}
              </div>
            ))}
          </section>

          <section aria-label="Педагоги" className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">Педагоги</p>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  setTeachers((previous) => [
                    ...previous,
                    { id: "", firstName: "", lastName: "", middleName: "", role: "Педагог" },
                  ])
                }
              >
                <Plus className="size-4" /> Добавить
              </Button>
            </div>
            {teachers.map((row, index) => (
              <div key={row.id || `new-${index}`} className="space-y-3 rounded-md border p-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Input
                    label="Фамилия"
                    value={row.lastName}
                    onChange={(e) => patchTeacher(index, { lastName: e.target.value })}
                  />
                  <Input
                    label="Имя"
                    value={row.firstName}
                    onChange={(e) => patchTeacher(index, { firstName: e.target.value })}
                  />
                  <Input
                    label="Отчество"
                    value={row.middleName}
                    onChange={(e) => patchTeacher(index, { middleName: e.target.value })}
                  />
                  <Input
                    label="Роль"
                    value={row.role}
                    onChange={(e) => patchTeacher(index, { role: e.target.value })}
                  />
                </div>
                <div className="flex justify-end">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      setTeachers((previous) =>
                        previous.filter((_, position) => position !== index),
                      )
                    }
                  >
                    <Trash2 className="size-4" /> Убрать
                  </Button>
                </div>
              </div>
            ))}
          </section>

          <section className="space-y-2">
            <p className="text-sm font-medium">Комментарий участнику</p>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Почему исправили — попадёт в письмо участнику"
            />
          </section>

          {error ? <p className="text-sm text-danger">{error}</p> : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Отмена
          </Button>
          <Button loading={correction.isPending} onClick={save}>
            Сохранить исправление
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
