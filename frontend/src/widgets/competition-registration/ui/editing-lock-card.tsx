import { Lock, LockOpen } from "lucide-react";
import { useState } from "react";

import { useSetSubmissionEditingLockMutation } from "@/features/competitions";
import { ApiError } from "@/shared/api";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  toast,
} from "@/shared/ui";

function formatInstant(iso: string | null): string {
  if (!iso) {
    return "—";
  }
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleString("ru-RU", { dateStyle: "medium", timeStyle: "short" });
}

/**
 * The festival-wide freeze: the last switch of the registration period.
 *
 * Lives beside the per-genre windows because that is where an organizer looks when
 * they are thinking about what is still open, and it is deliberately *not* one of
 * them. Closing a genre stops people getting in; whoever is already in goes on
 * replacing their backing track, which is the whole reason the upload deadlines are
 * later than the application ones. This ends that too, and it is thrown once — with
 * the final list in front of you, "кроме вокала" is not a thing anybody means.
 *
 * Behind a confirmation because its blast radius is every applicant at once, and
 * reversible because the decision is usually made a day early: a teacher writes in
 * with a track the organizer agreed to take, and the alternative to lifting it is
 * the organizer uploading files by hand for the rest of the week.
 */
export function EditingLockCard({
  competitionId,
  editingLockedAt,
  disabled = false,
}: {
  competitionId: string;
  /** When the freeze was thrown, or `null` while applicants may still act. */
  editingLockedAt: string | null;
  disabled?: boolean;
}): React.JSX.Element {
  const [confirming, setConfirming] = useState(false);
  const lock = useSetSubmissionEditingLockMutation();
  const locked = editingLockedAt !== null;

  const apply = (next: boolean): void => {
    lock.mutate(
      { competitionId, locked: next },
      {
        onSuccess: () => {
          setConfirming(false);
          toast.success(
            next
              ? "Редактирование заявок закрыто"
              : "Редактирование открыто — действуют сроки фестиваля",
          );
        },
        onError: (error) => {
          toast.error(
            error instanceof ApiError
              ? (error.problem?.detail ?? "Не удалось изменить доступ")
              : "Не удалось изменить доступ",
          );
        },
      },
    );
  };

  return (
    <Card className="shadow-none">
      <CardHeader className="flex-row items-center justify-between gap-3 pb-3">
        <CardTitle className="text-base">Редактирование заявок</CardTitle>
        <Badge variant={locked ? "warning" : "success"}>{locked ? "Закрыто" : "Открыто"}</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-muted-foreground text-sm">
          После закрытия приёма участник уже не правит состав заявки, но файлы — фонограммы, видео,
          фото, документы — меняет до своих сроков загрузки. Эта кнопка закрывает и их: всё, что
          может менять заявитель, замирает на всём фестивале сразу.
        </p>
        {locked ? (
          <Alert variant="warning" title="Заявители ничего не меняют">
            Закрыто {formatInstant(editingLockedAt)}. Приём новых заявок тоже остановлен. Вы как
            организатор по-прежнему правите заявки и догружаете файлы за участника.
          </Alert>
        ) : null}
        <Button
          type="button"
          variant={locked ? "outline" : "danger"}
          disabled={disabled}
          loading={lock.isPending}
          onClick={() => (locked ? apply(false) : setConfirming(true))}
        >
          {locked ? <LockOpen className="size-4" /> : <Lock className="size-4" />}
          {locked ? "Открыть редактирование" : "Закрыть редактирование полностью"}
        </Button>
      </CardContent>

      <Dialog open={confirming} onOpenChange={(next) => (next ? undefined : setConfirming(false))}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Закрыть редактирование полностью?</DialogTitle>
            <DialogDescription>
              Заявители перестанут менять заявки и файлы во всех жанрах сразу — включая тех, у кого
              вы просили исправления. Новые заявки тоже приниматься не будут. Решение обратимо:
              редактирование можно открыть этой же кнопкой.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setConfirming(false)}>
              Отмена
            </Button>
            <Button
              type="button"
              variant="danger"
              loading={lock.isPending}
              onClick={() => apply(true)}
            >
              Закрыть редактирование
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
