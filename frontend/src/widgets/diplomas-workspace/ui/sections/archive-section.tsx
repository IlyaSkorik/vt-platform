import { Archive, Download } from "lucide-react";
import { useMemo } from "react";
import {
  documentTypeConfig,
  type GenerationRunResponse,
  resolveMediaUrl,
  useGenerationArchive,
} from "@/features/diplomas";
import { Alert, Badge, Button, type ColumnDef, DataTable, EmptyState } from "@/shared/ui";
import { formatDateTime } from "../../lib/format";

/**
 * The generation history: every completed run, newest first.
 *
 * One table for both mechanisms — the numbered diploma package and the thank-you
 * runs — because the question it answers ("what did we generate, and where is that
 * ZIP?") does not care which pipeline produced the documents.
 *
 * Read-only by design. A run is a past event: nothing here edits or re-runs it, and
 * the only action is fetching its archive again when the download was lost.
 */
export function ArchiveSection(): React.JSX.Element {
  const archiveQuery = useGenerationArchive();

  const columns: ColumnDef<GenerationRunResponse>[] = useMemo(
    () => [
      {
        id: "generatedAt",
        header: "Дата генерации",
        cell: ({ row }) => (
          <span className="whitespace-nowrap">{formatDateTime(row.original.createdAt)}</span>
        ),
      },
      {
        accessorKey: "competition",
        header: "Фестиваль",
        // Null once a competition is deleted: the run still happened, so it is listed
        // without a name rather than dropped from the history.
        cell: ({ row }) => row.original.competition ?? "—",
      },
      {
        accessorKey: "documentType",
        header: "Тип документа",
        cell: ({ row }) => {
          const kind = documentTypeConfig(row.original.documentType);
          return (
            <Badge variant={kind.tone} size="sm">
              {kind.label}
            </Badge>
          );
        },
      },
      {
        accessorKey: "documents",
        header: "Документов",
        cell: ({ row }) => <RunCounts run={row.original} />,
      },
      {
        accessorKey: "user",
        header: "Пользователь",
        cell: ({ row }) => row.original.user ?? "—",
      },
      {
        id: "download",
        header: "",
        cell: ({ row }) => <DownloadCell run={row.original} />,
      },
    ],
    [],
  );

  return (
    <div className="flex flex-col gap-4">
      {archiveQuery.isError ? (
        <Alert variant="danger" title="Не удалось загрузить архив">
          {archiveQuery.error?.problem?.detail ?? "Попробуйте обновить страницу."}
        </Alert>
      ) : null}
      <DataTable
        columns={columns}
        data={archiveQuery.data ?? []}
        loading={archiveQuery.isLoading}
        emptyContent={
          <EmptyState
            icon={<Archive className="size-6" aria-hidden="true" />}
            title="Архив пуст"
            description="Здесь появится история генераций: дата, фестиваль, количество документов, кто запустил и повторное скачивание ZIP."
          />
        }
      />
    </div>
  );
}

/**
 * How many documents the run put out, and how much of that was new.
 *
 * Both numbers, because on a re-run they differ and only the pair explains the
 * archive: 40 documents in the ZIP of which 2 were created is a reprint, not a
 * second generation.
 */
function RunCounts({ run }: { run: GenerationRunResponse }): React.JSX.Element {
  return (
    <div className="flex flex-col">
      <span className="tabular-nums">{run.documents}</span>
      <span className="text-muted-foreground text-xs tabular-nums">
        новых: {run.created}
        {run.published > 0 ? ` · опубликовано: ${run.published}` : ""}
      </span>
    </div>
  );
}

/** Re-download the run's ZIP, when it produced one. */
function DownloadCell({ run }: { run: GenerationRunResponse }): React.JSX.Element {
  const href = resolveMediaUrl(run.zipUrl);
  if (!href) {
    // A run that published without printing built no archive — so there is nothing
    // to offer, and saying so beats a link that leads nowhere.
    return <span className="block text-right text-muted-foreground text-sm">без архива</span>;
  }
  return (
    <div className="flex justify-end">
      <Button asChild variant="outline" size="sm">
        <a href={href} download aria-label={`Скачать архив от ${formatDateTime(run.createdAt)}`}>
          <Download className="size-4" aria-hidden="true" />
          ZIP
        </a>
      </Button>
    </div>
  );
}
