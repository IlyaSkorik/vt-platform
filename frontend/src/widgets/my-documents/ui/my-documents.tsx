import {
  ChevronDown,
  ChevronRight,
  Download,
  FileArchive,
  FileText,
  Frown,
  RotateCcw,
} from "lucide-react";
import { useState } from "react";
import {
  type DocumentKindConfig,
  documentKind,
  documentRecipient,
  documentRows,
  documentSubtitle,
  downloadIndividualDiplomas,
  type MyDocument,
  useMyDocuments,
} from "@/features/my-documents";
import { resolveMediaUrl } from "@/shared/lib";
import { Badge, Button, Card, CardContent, EmptyState, Skeleton, toast } from "@/shared/ui";

/**
 * The tint each kind of document is marked with.
 *
 * Colour carries no information the text does not also carry — a diploma says
 * "Диплом" — so it is deliberately quiet: enough to tell two kinds apart while
 * scanning a long list, never the only thing saying which is which.
 */
const TONE_CLASSES: Record<DocumentKindConfig["tone"], string> = {
  diploma: "bg-warning/10 text-warning",
  gratitude: "bg-success/10 text-success",
  neutral: "bg-muted text-muted-foreground",
};

/** One document row: what it is, which competition, and a download. */
function DocumentRow({ document }: { document: MyDocument }): React.JSX.Element {
  const kind = documentKind(document.documentType);
  const KindIcon = kind.icon;
  const subtitle = documentSubtitle(document);
  const recipient = documentRecipient(document);
  const href = resolveMediaUrl(document.fileUrl);

  return (
    <li className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
      <div className="flex min-w-0 items-start gap-3">
        <span
          aria-hidden="true"
          className={`flex size-10 shrink-0 items-center justify-center rounded-lg ${TONE_CLASSES[kind.tone]}`}
        >
          <KindIcon className="size-5" />
        </span>
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-foreground">{kind.label}</p>
            {kind.showsDegree && document.degree ? (
              <Badge variant="success" size="sm">
                {document.degree}
              </Badge>
            ) : null}
          </div>
          {recipient ? (
            // The only thing telling two letters on one entry apart.
            <p className="wrap-anywhere text-foreground/80 text-sm">{recipient}</p>
          ) : null}
          {subtitle ? (
            <p className="wrap-anywhere text-muted-foreground text-sm">{subtitle}</p>
          ) : null}
          {kind.showsNumber && document.number ? (
            <p className="font-mono text-muted-foreground/80 text-xs tabular-nums tracking-wider">
              {document.number}
            </p>
          ) : null}
        </div>
      </div>
      {href ? (
        <Button asChild variant="outline" className="w-full shrink-0 sm:w-auto">
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Скачать: ${kind.label}${recipient ? `, ${recipient}` : ""}${subtitle ? ` — ${subtitle}` : ""} (PDF, откроется в новой вкладке)`}
          >
            <Download aria-hidden="true" />
            Скачать
          </a>
        </Button>
      ) : null}
    </li>
  );
}

/**
 * One entry's individual diplomas as a single row: what they are, and one archive.
 *
 * The count is the point of the row — twelve members are twelve documents that differ
 * only in the name on them, and offering twelve buttons is offering a chore. The list
 * underneath is collapsed rather than absent, because a parent came for exactly one
 * sheet and should not have to unpack a ZIP to get it.
 */
function DocumentBundleRow({
  submissionId,
  documents,
}: {
  submissionId: string;
  documents: MyDocument[];
}): React.JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const kind = documentKind(documents[0]?.documentType ?? "");
  const KindIcon = kind.icon;
  const subtitle = documents[0] ? documentSubtitle(documents[0]) : null;
  const degree = documents[0]?.degree;
  const ExpandIcon = expanded ? ChevronDown : ChevronRight;

  const download = async () => {
    setDownloading(true);
    try {
      await downloadIndividualDiplomas(submissionId);
    } catch {
      toast.error("Не удалось скачать архив. Попробуйте ещё раз.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <li className="py-4 first:pt-0 last:pb-0">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
        <div className="flex min-w-0 items-start gap-3">
          <span
            aria-hidden="true"
            className={`flex size-10 shrink-0 items-center justify-center rounded-lg ${TONE_CLASSES[kind.tone]}`}
          >
            <KindIcon className="size-5" />
          </span>
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-semibold text-foreground">{kind.label}</p>
              <Badge variant="secondary" size="sm">
                {documents.length} шт.
              </Badge>
              {kind.showsDegree && degree ? (
                <Badge variant="success" size="sm">
                  {degree}
                </Badge>
              ) : null}
            </div>
            {subtitle ? (
              <p className="wrap-anywhere text-muted-foreground text-sm">{subtitle}</p>
            ) : null}
            <button
              type="button"
              onClick={() => setExpanded((open) => !open)}
              aria-expanded={expanded}
              className="-mx-1 flex items-center gap-1 rounded px-1 text-primary text-sm hover:underline focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2"
            >
              <ExpandIcon aria-hidden="true" className="size-4" />
              {expanded ? "Скрыть список" : `Показать по одному (${documents.length})`}
            </button>
          </div>
        </div>
        <Button
          variant="outline"
          className="w-full shrink-0 sm:w-auto"
          loading={downloading}
          onClick={() => void download()}
          aria-label={`Скачать архив: ${kind.label}, ${documents.length} шт.${subtitle ? ` — ${subtitle}` : ""} (ZIP)`}
        >
          <FileArchive aria-hidden="true" />
          Скачать архивом
        </Button>
      </div>

      {expanded ? (
        <ul className="mt-3 space-y-1 border-border border-l pl-4 sm:ml-13">
          {documents.map((document) => {
            const href = resolveMediaUrl(document.fileUrl);
            const who = documentRecipient(document) ?? document.participantName ?? "Без имени";
            return (
              <li
                key={document.id}
                className="flex flex-wrap items-center justify-between gap-2 py-1"
              >
                <span className="wrap-anywhere text-foreground/80 text-sm">{who}</span>
                {href ? (
                  <Button asChild variant="outline" size="xs">
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Скачать диплом: ${who} (PDF, откроется в новой вкладке)`}
                    >
                      <Download aria-hidden="true" />
                      Скачать
                    </a>
                  </Button>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </li>
  );
}

function DocumentsSkeleton(): React.JSX.Element {
  return (
    <Card aria-busy="true">
      <CardContent className="space-y-6 py-6">
        {["a", "b"].map((key) => (
          <div key={key} className="flex items-center justify-between gap-6">
            <div className="space-y-2">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-4 w-56" />
            </div>
            <Skeleton className="h-9 w-28" />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

/**
 * The participant's issued documents.
 *
 * A read-only list of whatever the platform has issued to this user. Documents
 * arrive here on their own — a thank-you letter is published the moment the
 * organizer generates it — so an empty list says "not yet", never "something went
 * wrong".
 */
export function MyDocuments(): React.JSX.Element {
  const query = useMyDocuments();

  if (query.isPending) {
    return <DocumentsSkeleton />;
  }
  if (query.isError) {
    return (
      <Card>
        <CardContent className="py-4">
          <EmptyState
            icon={<Frown aria-hidden="true" />}
            title="Не удалось загрузить документы"
            description="Проверьте соединение и попробуйте снова."
            action={
              <Button
                onClick={() => void query.refetch()}
                loading={query.isFetching}
                leftIcon={<RotateCcw aria-hidden="true" />}
              >
                Повторить
              </Button>
            }
          />
        </CardContent>
      </Card>
    );
  }

  if (query.data.length === 0) {
    return (
      <Card>
        <CardContent className="py-4">
          <EmptyState
            icon={<FileText aria-hidden="true" />}
            title="Документов пока нет"
            description="Дипломы и благодарности появятся здесь после того, как организатор их сформирует. Ничего делать не нужно."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="px-6 py-6 sm:px-8">
        <ul className="divide-y divide-border">
          {documentRows(query.data).map((row) =>
            row.kind === "bundle" ? (
              <DocumentBundleRow
                key={row.key}
                submissionId={row.submissionId}
                documents={row.documents}
              />
            ) : (
              <DocumentRow key={row.key} document={row.document} />
            ),
          )}
        </ul>
      </CardContent>
    </Card>
  );
}
