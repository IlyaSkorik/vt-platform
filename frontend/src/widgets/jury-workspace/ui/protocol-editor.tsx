import { ArrowDown, ArrowUp, ExternalLink, Link2, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useMemo } from "react";

import {
  type AwardKind,
  moveRow,
  PROTOCOL_STATUS_LABELS,
  type Protocol,
  type ProtocolRow,
  undecidedCount,
  useAwardProtocolRows,
  useRemoveProtocolRow,
  useRenumberProtocolRows,
  useReorderProtocolRows,
  useSyncProtocolRows,
  useUnpublishProtocol,
} from "@/features/jury-protocols";
import { ApiError } from "@/shared/api";
import { Badge, Button, IconButton, Select, type SelectOption, toast } from "@/shared/ui";

import { formatPublishedAt } from "../lib/format";
import { PublicationStatus } from "./publication-status";
import { PublishProtocolDialog } from "./publish-protocol-dialog";

interface ProtocolEditorProps {
  protocol: Protocol;
}

/** The one message every failed write on this screen falls back to. */
function failureMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? (error.problem?.detail ?? fallback) : fallback;
}

/**
 * The jury's table: the acts in the order they performed, and a dropdown per row.
 *
 * The interaction is deliberately as small as it can be. A result is set by picking it and
 * that is the whole gesture — no edit mode, no save button, no confirmation — because a jury
 * enters "Лауреат II степени" and corrects it to "Лауреат I степени" ten minutes later, and a
 * screen that made the second gesture heavier than the first would be fighting the work. The
 * empty option is a real choice, not a placeholder: an act that did not appear has a row and
 * no result.
 *
 * What the screen *is* emphatic about is the gap between the table and the page: once
 * published, edits stay private until somebody publishes again, and the banner says so rather
 * than letting an organizer assume a correction is already out there.
 */
export function ProtocolEditor({ protocol }: ProtocolEditorProps): React.JSX.Element {
  const award = useAwardProtocolRows(protocol.id);
  const removeRow = useRemoveProtocolRow(protocol.id);
  const reorder = useReorderProtocolRows(protocol.id);
  const renumber = useRenumberProtocolRows(protocol.id);
  const sync = useSyncProtocolRows(protocol.id);
  const unpublish = useUnpublishProtocol(protocol.id);

  const blanks = undecidedCount(protocol);

  /** The award dropdown's options: the served vocabulary, plus "not decided". */
  const awardOptions: SelectOption[] = useMemo(
    () => [
      { value: "", label: "— не решено —" },
      ...protocol.awardOptions.map((option) => ({ value: option.value, label: option.label })),
    ],
    [protocol.awardOptions],
  );

  const handleAward = useCallback(
    async (rowId: string, value: string): Promise<void> => {
      try {
        // An empty selection is a cleared result, which is why it travels as an explicit
        // `null` rather than as an omitted key.
        await award.mutateAsync([{ rowId, award: value === "" ? null : (value as AwardKind) }]);
      } catch (error) {
        toast.error(failureMessage(error, "Не удалось сохранить результат."));
      }
    },
    [award],
  );

  const handleMove = useCallback(
    async (index: number, direction: -1 | 1): Promise<void> => {
      const ordered = moveRow(protocol.rows, index, index + direction);
      try {
        await reorder.mutateAsync(ordered.map((row) => row.id));
      } catch (error) {
        toast.error(failureMessage(error, "Не удалось изменить порядок."));
      }
    },
    [protocol.rows, reorder],
  );

  const handleRemove = useCallback(
    async (row: ProtocolRow): Promise<void> => {
      try {
        await removeRow.mutateAsync(row.id);
        toast.success("Строка удалена");
      } catch (error) {
        toast.error(failureMessage(error, "Не удалось удалить строку."));
      }
    },
    [removeRow],
  );

  const handleSync = useCallback(async (): Promise<void> => {
    try {
      const updated = await sync.mutateAsync();
      const added = updated.rows.length - protocol.rows.length;
      toast.success(added > 0 ? `Добавлено строк: ${added}` : "Новых выступлений нет");
    } catch (error) {
      toast.error(failureMessage(error, "Не удалось обновить состав."));
    }
  }, [sync, protocol.rows.length]);

  const handleRenumber = useCallback(async (): Promise<void> => {
    try {
      await renumber.mutateAsync();
      toast.success("Номера выставлены заново");
    } catch (error) {
      toast.error(failureMessage(error, "Не удалось перенумеровать."));
    }
  }, [renumber]);

  const handleUnpublish = useCallback(async (): Promise<void> => {
    try {
      await unpublish.mutateAsync();
      toast.success("Протокол снят с публикации. Выданные дипломы остаются у участников.");
    } catch (error) {
      toast.error(failureMessage(error, "Не удалось снять с публикации."));
    }
  }, [unpublish]);

  const publicUrl = protocol.path == null ? null : `${window.location.origin}${protocol.path}`;

  const handleCopyLink = useCallback(async (): Promise<void> => {
    if (publicUrl == null) {
      return;
    }
    try {
      await navigator.clipboard.writeText(publicUrl);
      toast.success("Ссылка скопирована");
    } catch {
      // Clipboard access can be refused outright (an insecure origin, a denied permission).
      // Showing the URL is a worse experience than copying it and a better one than silence.
      toast.error(`Не удалось скопировать. Ссылка: ${publicUrl}`);
    }
  }, [publicUrl]);

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate font-semibold text-base text-foreground">{protocol.name}</h3>
            <Badge variant={protocol.status === "PUBLISHED" ? "success" : "neutral"}>
              {PROTOCOL_STATUS_LABELS[protocol.status]}
            </Badge>
            {protocol.revision > 0 ? (
              <Badge variant="neutral">Ревизия {protocol.revision}</Badge>
            ) : null}
          </div>
          <p className="text-muted-foreground text-sm">
            Строк: {protocol.rows.length}
            {blanks > 0 ? ` · без результата: ${blanks}` : " · все результаты проставлены"}
            {protocol.publishedAt
              ? ` · опубликован ${formatPublishedAt(protocol.publishedAt)}`
              : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleSync} loading={sync.isPending}>
            <RefreshCw className="size-4" aria-hidden="true" />
            Обновить состав
          </Button>
          <Button variant="outline" size="sm" onClick={handleRenumber} loading={renumber.isPending}>
            Перенумеровать
          </Button>
          <PublishProtocolDialog protocol={protocol} />
        </div>
      </header>

      <PublicationStatus protocol={protocol} />

      {protocol.hasUnpublishedChanges ? (
        <p className="rounded-lg border border-warning/40 bg-warning-surface px-3 py-2 text-sm">
          Есть изменения после публикации. На странице результатов по-прежнему ревизия{" "}
          {protocol.revision} — нажмите «Опубликовать заново», чтобы обновить её и дипломы.
        </p>
      ) : null}

      {protocol.path != null ? (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm">
          <Link2 className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <code className="min-w-0 flex-1 truncate">{publicUrl}</code>
          <Button variant="outline" size="sm" onClick={handleCopyLink}>
            Скопировать
          </Button>
          <Button variant="ghost" size="sm" asChild>
            <a href={protocol.path} target="_blank" rel="noreferrer">
              <ExternalLink className="size-4" aria-hidden="true" />
              Открыть
            </a>
          </Button>
          {protocol.status === "PUBLISHED" ? (
            <Button
              variant="outline"
              size="sm"
              onClick={handleUnpublish}
              loading={unpublish.isPending}
            >
              Снять с публикации
            </Button>
          ) : null}
        </div>
      ) : null}

      {protocol.rows.length === 0 ? (
        <p className="rounded-lg border border-border border-dashed px-3 py-6 text-center text-muted-foreground text-sm">
          В протоколе нет строк. Нажмите «Обновить состав», чтобы подтянуть выступления этой жанра в
          порядке программы.
        </p>
      ) : (
        <div className="scrollbar-custom overflow-x-auto rounded-lg border border-border">
          {/* `table-fixed` on purpose: with an auto layout a cell grows to fit its text and
              `truncate` never engages, so one long organization name is enough to push the
              table past its container and demand a sideways scroll. Fixed widths make the
              cells definite, which is what lets long values be cut instead.
              The floor is 34rem — under the width this pane gets even with the nomination
              list beside it, so the table scrolls only on a genuinely narrow screen. */}
          <table className="w-full min-w-[34rem] table-fixed border-collapse text-sm">
            <thead>
              <tr className="border-border border-b bg-muted/40 text-left">
                <th scope="col" className="w-14 px-3 py-2 font-medium">
                  №
                </th>
                {/* Participant and act in one column, stacked. They were two, and the four
                    fixed columns then left under 200px for both — the jury reads a line as
                    "кто и что", so stacking them costs nothing and buys the width back. */}
                <th scope="col" className="px-3 py-2 font-medium">
                  Участник и номер
                </th>
                {/* Wide enough for "Номинант на Гран-при", the longest award, and pinned with
                    a min-width because `w-` alone is a hint the table layout may ignore — and
                    a squeezed dropdown wraps its label inside a fixed-height trigger. */}
                <th scope="col" className="w-[15rem] min-w-[15rem] px-3 py-2 font-medium">
                  Результат
                </th>
                <th scope="col" className="w-28 px-3 py-2 font-medium">
                  <span className="sr-only">Действия</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {protocol.rows.map((row, index) => (
                <tr key={row.id} className="border-border border-b last:border-b-0">
                  <td className="px-3 py-2 text-muted-foreground tabular-nums">{row.number}</td>
                  <td className="px-3 py-2">
                    <span className="block truncate font-medium">
                      {row.participants.join(", ") || "—"}
                    </span>
                    {/* The act, and the school after it: two facts that identify one line and
                        neither of which needs a column of its own here. */}
                    <span className="block truncate text-muted-foreground text-xs">
                      {row.organization ? `${row.title} · ${row.organization}` : row.title}
                    </span>
                    {row.missingPerformance ? (
                      <span className="block truncate text-warning text-xs">
                        Заявка удалена — строка осталась в протоколе
                      </span>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 align-middle">
                    <Select
                      size="sm"
                      aria-label={`Результат: ${row.title}`}
                      options={awardOptions}
                      value={row.award ?? ""}
                      onValueChange={(value) => void handleAward(row.id, value)}
                      // The trigger is a fixed-height row, so a wrapped label does not make it
                      // taller — it spills out of it. Keeping the award on one line and letting
                      // it truncate is the only version of this that stays readable.
                      className="[&>span]:min-w-0 [&>span]:truncate whitespace-nowrap"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center justify-end gap-1">
                      <IconButton
                        variant="ghost"
                        size="sm"
                        aria-label="Выше"
                        icon={<ArrowUp className="size-4" aria-hidden="true" />}
                        disabled={index === 0 || reorder.isPending}
                        onClick={() => void handleMove(index, -1)}
                      />
                      <IconButton
                        variant="ghost"
                        size="sm"
                        aria-label="Ниже"
                        icon={<ArrowDown className="size-4" aria-hidden="true" />}
                        disabled={index === protocol.rows.length - 1 || reorder.isPending}
                        onClick={() => void handleMove(index, 1)}
                      />
                      <IconButton
                        variant="ghost"
                        size="sm"
                        aria-label={`Удалить строку: ${row.title}`}
                        icon={<Trash2 className="size-4" aria-hidden="true" />}
                        onClick={() => void handleRemove(row)}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
