import { CalendarClock, CircleCheck } from "lucide-react";
import { useEffect, useState } from "react";
import {
  useResumeNominationRegistrationMutation,
  useScheduleNominationRegistrationMutation,
  useStopNominationRegistrationMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import type { _Category } from "@/shared/api/generated/model-competitions";
import { Badge, Button, DateTimePicker, toast } from "@/shared/ui";

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

  const [opensAt, setOpensAt] = useState(() => isoToLocalInput(category.registrationOpensAt));
  const [closesAt, setClosesAt] = useState(() => isoToLocalInput(category.registrationClosesAt));

  // Keep local inputs in sync when the competition is refreshed from the server.
  useEffect(() => {
    setOpensAt(isoToLocalInput(category.registrationOpensAt));
    setClosesAt(isoToLocalInput(category.registrationClosesAt));
  }, [category.registrationOpensAt, category.registrationClosesAt]);

  const state = deriveState(category);
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
      });
      toast.success("Окно регистрации сохранено");
    } catch (error) {
      toast.error(apiErrorMessage(error, "Не удалось сохранить окно регистрации"));
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

  return (
    <div className="space-y-3 rounded-md border border-border bg-muted/30 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-medium text-sm">
          <CalendarClock className="size-4 text-muted-foreground" aria-hidden="true" />
          {category.name}
        </div>
        <Badge variant={state.variant} size="sm">
          {state.label}
        </Badge>
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
          Сохранить окно
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
      </div>
    </div>
  );
}
