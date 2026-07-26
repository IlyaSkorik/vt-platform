import { Download, FileText, Frown, RotateCcw } from "lucide-react";
import {
  documentKind,
  documentRecipient,
  documentSubtitle,
  type MyDocument,
  useMyDocuments,
} from "@/features/my-documents";
import { resolveMediaUrl } from "@/shared/lib";
import { Badge, Button, Card, CardContent, EmptyState, Skeleton } from "@/shared/ui";

/** One document row: what it is, which competition, and a download. */
function DocumentRow({ document }: { document: MyDocument }): React.JSX.Element {
  const kind = documentKind(document.documentType);
  const subtitle = documentSubtitle(document);
  const recipient = documentRecipient(document);
  const href = resolveMediaUrl(document.fileUrl);

  return (
    <li className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
      <div className="flex min-w-0 items-start gap-3">
        <span aria-hidden="true" className="text-2xl leading-none">
          {kind.icon}
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
          {query.data.map((document) => (
            <DocumentRow key={document.id} document={document} />
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
