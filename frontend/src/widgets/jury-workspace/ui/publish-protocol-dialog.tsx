import { Send } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import {
  canPublish,
  type Protocol,
  type ProtocolColumnKey,
  undecidedCount,
  usePublishProtocol,
} from "@/features/jury-protocols";
import { ApiError } from "@/shared/api";
import {
  Button,
  Checkbox,
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Switch,
  toast,
} from "@/shared/ui";

interface PublishProtocolDialogProps {
  protocol: Protocol;
}

/**
 * The publish dialog — where the organizer decides what the world sees.
 *
 * It asks two questions and no more, because pressing the button does three things and the
 * organizer has to understand all of them before it happens:
 *
 * - **which columns the public page shows.** Asked here rather than in a settings screen
 *   because it is decided in the same breath as publishing ("покажем педагога"), and because
 *   a protocol that lists a child's school and teacher to the whole internet is a different
 *   document from one that lists the award. The dialog opens on whatever is currently chosen,
 *   which on a first publication is the platform's narrow default.
 * - **whether the participants are written to.** On by default — the letter is the point of
 *   publishing — and turned off for a re-publication that only fixes a column selection,
 *   where a second letter to thirty studios would be noise.
 *
 * The summary above the fields is deliberately blunt about what is about to happen, including
 * the rows with no result: those are published as blank lines, which is right for an act that
 * did not appear and wrong if the jury simply has not finished.
 */
export function PublishProtocolDialog({ protocol }: PublishProtocolDialogProps): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const [columns, setColumns] = useState<Set<ProtocolColumnKey>>(
    () => new Set(protocol.publicColumns.map((column) => column.key)),
  );
  const [notify, setNotify] = useState(true);

  const publish = usePublishProtocol(protocol.id);

  const decided = protocol.rows.length - undecidedCount(protocol);
  const blanks = undecidedCount(protocol);
  const republishing = protocol.revision > 0;

  const handleOpenChange = useCallback(
    (next: boolean): void => {
      setOpen(next);
      if (next) {
        // Re-seeded on every open: the current selection is the honest starting point, and a
        // stale one from a dialog closed ten minutes ago is not.
        setColumns(new Set(protocol.publicColumns.map((column) => column.key)));
        setNotify(true);
      }
    },
    [protocol.publicColumns],
  );

  function toggleColumn(key: ProtocolColumnKey, on: boolean): void {
    const next = new Set(columns);
    if (on) {
      next.add(key);
    } else {
      next.delete(key);
    }
    setColumns(next);
  }

  const orderedColumns = useMemo(
    () => protocol.availableColumns.filter((column) => columns.has(column.key)),
    [protocol.availableColumns, columns],
  );

  async function handlePublish(): Promise<void> {
    try {
      const result = await publish.mutateAsync({
        columns: orderedColumns.map((column) => column.key),
        notify,
      });
      const parts = [
        `Ревизия ${result.protocol.revision}`,
        `дипломов: ${result.diplomasAwarded}`,
        notify ? `писем: ${result.lettersSent}` : "без писем",
      ];
      toast.success(`Протокол опубликован. ${parts.join(", ")}.`);
      // Not a toast among toasts: a participant with a result and no document is the one
      // outcome an organizer has to act on, and it normally means the nomination has no
      // diploma template assigned yet.
      if (result.diplomasMissing > 0) {
        toast.error(
          `Без диплома осталось ${result.diplomasMissing} — проверьте, назначен ли шаблон диплома этого жанра.`,
        );
      }
      if (notify && result.lettersSkipped > 0) {
        toast.error(`Не отправлено писем: ${result.lettersSkipped} — у заявителя нет e-mail.`);
      }
      setOpen(false);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? (error.problem?.detail ?? "Не удалось опубликовать протокол.")
          : "Не удалось опубликовать протокол.";
      toast.error(message);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <Button
        onClick={() => handleOpenChange(true)}
        disabled={!canPublish(protocol)}
        // The reason, not just the disabled state: a jury that has entered nothing should be
        // told what is missing rather than left clicking a dead button.
        title={canPublish(protocol) ? undefined : "Проставьте хотя бы один результат"}
      >
        <Send className="size-4" aria-hidden="true" />
        {republishing ? "Опубликовать заново" : "Опубликовать"}
      </Button>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{republishing ? "Публикация исправлений" : "Публикация итогов"}</DialogTitle>
          <DialogDescription>
            {republishing
              ? `Страница обновится до ревизии ${protocol.revision + 1}. Ссылка не изменится, дипломы будут перевыпущены с новыми степенями.`
              : "Итоги станут публичными, дипломы получат степень и появятся в личных кабинетах участников."}
          </DialogDescription>
        </DialogHeader>

        <dl className="grid grid-cols-2 gap-2 rounded-lg border border-border bg-muted/40 p-3 text-sm">
          <dt className="text-muted-foreground">Результатов проставлено</dt>
          <dd className="text-right font-medium">{decided}</dd>
          <dt className="text-muted-foreground">Строк без результата</dt>
          <dd className="text-right font-medium">{blanks}</dd>
        </dl>
        {blanks > 0 ? (
          <p className="text-muted-foreground text-sm">
            Строки без результата будут опубликованы пустыми — так и должно быть для номера, который
            не вышел на сцену.
          </p>
        ) : null}

        <fieldset className="flex flex-col gap-2">
          <legend className="font-medium text-foreground text-sm">Колонки протокола</legend>
          <p className="text-muted-foreground text-sm">
            Что увидит любой, кто откроет ссылку. Снятая колонка не попадает в ответ сервера вообще.
          </p>
          <div className="scrollbar-custom flex max-h-56 flex-col gap-2 overflow-y-auto rounded-lg border border-border p-3">
            {protocol.availableColumns.map((column) => (
              <Checkbox
                key={column.key}
                label={column.label}
                checked={columns.has(column.key)}
                onCheckedChange={(checked) => toggleColumn(column.key, checked === true)}
              />
            ))}
          </div>
          {columns.size === 0 ? (
            <p className="text-muted-foreground text-sm">
              Ничего не выбрано — страница покажет колонки по умолчанию: №, участник, номер,
              результат.
            </p>
          ) : null}
        </fieldset>

        <Switch
          label="Отправить письма участникам"
          description="По одному письму на аккаунт заявителя со всеми его результатами в этой номинации."
          checked={notify}
          onCheckedChange={setNotify}
        />

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="ghost">Отмена</Button>
          </DialogClose>
          <Button onClick={handlePublish} loading={publish.isPending}>
            {republishing ? "Опубликовать ревизию" : "Опубликовать"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
