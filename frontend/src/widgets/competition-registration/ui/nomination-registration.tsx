import { CalendarClock, CircleCheck, ListOrdered, Lock, LockOpen } from "lucide-react";
import { useEffect, useState } from "react";
import {
  useDisableNominationWaitlistMutation,
  useEnableNominationWaitlistMutation,
  useResumeNominationRegistrationMutation,
  useScheduleNominationRegistrationMutation,
  useSetSubmissionEditingLockMutation,
  useStopNominationRegistrationMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import type { _Category } from "@/shared/api/generated/model-competitions";
import {
  Badge,
  Button,
  DateTimePicker,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  toast,
} from "@/shared/ui";

interface NominationRegistrationProps {
  competitionId: string;
  category: _Category;
  /** Registration control is disabled once the competition is archived. */
  disabled?: boolean;
}

interface RegistrationState {
  label: string;
  variant: "success" | "warning" | "secondary";
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

/** ISO instant → `datetime-local` input value (in the viewer's local time zone). */
function isoToLocalInput(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** `datetime-local` input value → ISO instant, or null when empty/invalid. */
function localInputToIso(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function formatInstant(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("ru-RU", { dateStyle: "medium", timeStyle: "short" });
}

/** Whether the genre is shut right now — by its own dates or by an early stop. */
function isClosedNow(category: _Category): boolean {
  if (category.registrationStopped) return true;
  const opensMs = category.registrationOpensAt ? Date.parse(category.registrationOpensAt) : null;
  const closesMs = category.registrationClosesAt ? Date.parse(category.registrationClosesAt) : null;
  if (opensMs === null && closesMs === null) return true; // unconfigured — closed
  const now = Date.now();
  if (opensMs !== null && now < opensMs) return true;
  if (closesMs !== null && now > closesMs) return true;
  return false;
}

function deriveState(category: _Category): RegistrationState {
  if (category.registrationStopped) {
    return { label: "Регистрация остановлена", variant: "warning" };
  }
  const opensMs = category.registrationOpensAt ? Date.parse(category.registrationOpensAt) : null;
  const closesMs = category.registrationClosesAt ? Date.parse(category.registrationClosesAt) : null;
  const configured = opensMs !== null || closesMs !== null;
  if (!configured) {
    return { label: "Регистрация не настроена", variant: "secondary" };
  }
  const now = Date.now();
  if (opensMs !== null && now < opensMs) {
    return {
      label: `Откроется ${formatInstant(category.registrationOpensAt)}`,
      variant: "secondary",
    };
  }
  if (closesMs !== null && now > closesMs) {
    return { label: "Регистрация закрыта", variant: "warning" };
  }
  return { label: "Регистрация открыта", variant: "success" };
}

function apiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.problem?.detail ?? fallback;
  }
  return fallback;
}

export function NominationRegistration({
  competitionId,
  category,
  disabled = false,
}: NominationRegistrationProps): React.JSX.Element {
  const schedule = useScheduleNominationRegistrationMutation();
  const stop = useStopNominationRegistrationMutation();
  const resume = useResumeNominationRegistrationMutation();
  const enableWaitlist = useEnableNominationWaitlistMutation();
  const disableWaitlist = useDisableNominationWaitlistMutation();
  const editingLock = useSetSubmissionEditingLockMutation();
  const [confirmingLock, setConfirmingLock] = useState(false);

  const [opensAt, setOpensAt] = useState(() => isoToLocalInput(category.registrationOpensAt));
  const [closesAt, setClosesAt] = useState(() => isoToLocalInput(category.registrationClosesAt));
  const [heldAt, setHeldAt] = useState(() => isoToLocalInput(category.heldAt));

  // Keep local inputs in sync when the competition is refreshed from the server.
  useEffect(() => {
    setOpensAt(isoToLocalInput(category.registrationOpensAt));
    setClosesAt(isoToLocalInput(category.registrationClosesAt));
    setHeldAt(isoToLocalInput(category.heldAt));
  }, [category.registrationOpensAt, category.registrationClosesAt, category.heldAt]);

  const state = deriveState(category);
  const closedNow = isClosedNow(category);
  const locked = category.editingLockedAt !== null;
  const invalidRange = opensAt !== "" && closesAt !== "" && new Date(closesAt) < new Date(opensAt);

  const handleSaveWindow = async (): Promise<void> => {
    if (invalidRange) {
      toast.error("Окончание регистрации не может быть раньше начала");
      return;
    }
    try {
      await schedule.mutateAsync({
        competitionId,
        categoryId: category.id,
        opensAt: localInputToIso(opensAt),
        closesAt: localInputToIso(closesAt),
        heldAt: localInputToIso(heldAt),
      });
      toast.success("Сохранено");
    } catch (error) {
      toast.error(apiErrorMessage(error, "Не удалось сохранить"));
    }
  };

  const handleStop = async (): Promise<void> => {
    try {
      await stop.mutateAsync({ competitionId, categoryId: category.id });
      toast.success("Регистрация в номинации остановлена");
    } catch (error) {
      toast.error(apiErrorMessage(error, "Не удалось остановить регистрацию"));
    }
  };

  const handleResume = async (): Promise<void> => {
    try {
      await resume.mutateAsync({ competitionId, categoryId: category.id });
      toast.success("Регистрация в номинации возобновлена");
    } catch (error) {
      toast.error(apiErrorMessage(error, "Не удалось возобновить регистрацию"));
    }
  };

  const handleSetLock = async (locked: boolean): Promise<void> => {
    try {
      await editingLock.mutateAsync({ competitionId, categoryId: category.id, locked });
      setConfirmingLock(false);
      toast.success(
        locked
          ? `Редактирование в жанре «${category.name}» закрыто`
          : `Редактирование в жанре «${category.name}» открыто`,
      );
    } catch (error) {
      toast.error(apiErrorMessage(error, "Не удалось изменить замок редактирования"));
    }
  };

  const handleToggleWaitlist = async (): Promise<void> => {
    const mutation = category.waitlistEnabled ? disableWaitlist : enableWaitlist;
    try {
      await mutation.mutateAsync({ competitionId, categoryId: category.id });
      toast.success(
        category.waitlistEnabled
          ? "Лист ожидания закрыт для новых заявок"
          : "Лист ожидания включён",
      );
    } catch (error) {
      toast.error(apiErrorMessage(error, "Не удалось изменить лист ожидания"));
    }
  };

  return (
    <div className="space-y-3 rounded-md border border-border bg-muted/30 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-medium text-sm">
          <CalendarClock className="size-4 text-muted-foreground" aria-hidden="true" />
          {category.name}
        </div>
        <div className="flex items-center gap-2">
          {/* Своя плашка, а не «регистрация закрыта»: закрытый приём и замороженная
              правка — разные ответы заявителю, и организатор смотрит сюда, чтобы
              понять, что ещё можно поменять в жанре. */}
          {locked ? (
            <Badge variant="warning" size="sm">
              Правки закрыты {formatInstant(category.editingLockedAt)}
            </Badge>
          ) : null}
          {category.waitlistEnabled ? (
            <Badge variant={closedNow ? "info" : "secondary"} size="sm">
              {closedNow ? "Лист ожидания открыт" : "Лист ожидания наготове"}
            </Badge>
          ) : null}
          <Badge variant={state.variant} size="sm">
            {state.label}
          </Badge>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <DateTimePicker
          label="Начало приёма заявок"
          value={opensAt}
          disabled={disabled}
          onChange={setOpensAt}
        />
        <DateTimePicker
          label="Окончание приёма заявок"
          value={closesAt}
          disabled={disabled}
          onChange={setClosesAt}
          {...(invalidRange ? { error: "Раньше начала" } : {})}
        />
        {/* Not part of the window above, and the reason it is on this card
            anyway: a festival running over several days judges one genre a day,
            so this is the date an applicant is actually asking about. Leaving
            it empty is normal — a one-afternoon festival has nothing to say
            here, and the public card then shows only the intake window. */}
        <DateTimePicker
          label="Дата проведения номинации"
          value={heldAt}
          disabled={disabled}
          onChange={setHeldAt}
        />
      </div>
      <p className="text-muted-foreground text-xs">
        Приём заявок в номинации открыт только внутри окна. Если окно не задано — регистрация
        закрыта. Текущее окно: {formatInstant(category.registrationOpensAt)} —{" "}
        {formatInstant(category.registrationClosesAt)}.
      </p>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          onClick={() => void handleSaveWindow()}
          loading={schedule.isPending}
          disabled={disabled || invalidRange}
        >
          <CircleCheck className="size-3.5" aria-hidden="true" />
          Сохранить
        </Button>
        {category.registrationStopped ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void handleResume()}
            loading={resume.isPending}
            disabled={disabled}
          >
            Возобновить регистрацию
          </Button>
        ) : (
          <Button
            type="button"
            size="sm"
            variant="danger"
            onClick={() => void handleStop()}
            loading={stop.isPending}
            disabled={disabled}
          >
            Остановить регистрацию
          </Button>
        )}
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => void handleToggleWaitlist()}
          loading={enableWaitlist.isPending || disableWaitlist.isPending}
          disabled={disabled}
        >
          <ListOrdered className="size-3.5" aria-hidden="true" />
          {category.waitlistEnabled ? "Выключить лист ожидания" : "Включить лист ожидания"}
        </Button>
        {/* Закрытие спрашивает, открытие — нет: вернуть людям доступ должно быть
            легче, чем отнять, и решение закрыть обычно принимают за день до срока. */}
        {locked ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void handleSetLock(false)}
            loading={editingLock.isPending}
            disabled={disabled}
          >
            <LockOpen className="size-3.5" aria-hidden="true" />
            Открыть редактирование
          </Button>
        ) : (
          <Button
            type="button"
            size="sm"
            variant="danger"
            onClick={() => setConfirmingLock(true)}
            loading={editingLock.isPending}
            disabled={disabled}
          >
            <Lock className="size-3.5" aria-hidden="true" />
            Закрыть редактирование
          </Button>
        )}
      </div>
      <p className="text-muted-foreground text-xs">
        {locked
          ? "Заявители этого жанра не меняют ни состав, ни файлы. Вас замок не касается: правьте заявки и догружайте файлы за участника как обычно."
          : "Закрытый приём не трогает файлы: фонограммы, видео и документы участник меняет до своих сроков загрузки. «Закрыть редактирование» останавливает и это — в этом жанре."}
      </p>
      <Dialog open={confirmingLock} onOpenChange={setConfirmingLock}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Закрыть редактирование в жанре «{category.name}»?</DialogTitle>
            <DialogDescription>
              Заявители этого жанра перестанут менять состав участников и файлы — фонограммы, видео,
              документы, — даже если сроки загрузки ещё не вышли и даже если вы сами вернули заявку
              на доработку. Приём новых заявок в жанр тоже остановится. Оплату это не трогает.
              Другие жанры продолжают работать как раньше. Открыть обратно можно в любой момент.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setConfirmingLock(false)}>
              Отмена
            </Button>
            <Button
              type="button"
              variant="danger"
              loading={editingLock.isPending}
              onClick={() => void handleSetLock(true)}
            >
              Закрыть редактирование
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <p className="text-muted-foreground text-xs">
        {category.waitlistEnabled
          ? "Пока приём закрыт, участники могут встать в лист ожидания — без оплаты и вне основной программы. Перевести их в конкурс или отменить можно в обработке заявок."
          : "Когда приём закрыт, жанр просто недоступен. Включите лист ожидания, чтобы опоздавшие всё же могли подать заявку."}
      </p>
    </div>
  );
}
