import { useMemo } from "react";
import { useParams } from "react-router";

import {
  type PublicProtocol,
  type PublicProtocolRow,
  usePublicProtocol,
} from "@/features/public-protocol";
import { APP_NAME } from "@/shared/config";
import { cn } from "@/shared/lib";
import { useSeo } from "@/shared/seo";
import { Badge, EmptyState, LoadingState } from "@/shared/ui";

const PUBLISHED_AT_FORMATTER = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "long",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function formatPublishedAt(iso: string | null): string {
  if (!iso) {
    return "";
  }
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? "" : PUBLISHED_AT_FORMATTER.format(parsed);
}

/**
 * `/protocol/:slug` — the published results of one nomination.
 *
 * Unauthenticated by design, and unlike a programme link this one is *meant* to be found: it
 * is what the competition's landing page links under "Результаты" and what the letter sent to
 * every participant points at. It renders whatever columns the organizer published and does
 * not know which ones those are, which is exactly why an unpublished column cannot appear
 * here — the cells for it do not exist in the payload.
 *
 * A document, not a dashboard: nothing here polls, because results change when somebody
 * deliberately publishes a correction. When that happens the revision goes up and the page
 * says so, so a reader who saw the earlier version can tell that this is a different one.
 */
export function PublicProtocolPage(): React.JSX.Element {
  const { slug } = useParams();
  const { data: protocol, isLoading, isError } = usePublicProtocol(slug);
  // Same reasoning as the programme: a results protocol is a list of children's
  // full names, ages and marks. The link is meant to be forwarded, not found.
  useSeo({ title: "Протокол результатов", robots: "noindex" });

  if (isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-6">
        <LoadingState label="Загружаем протокол…" />
      </div>
    );
  }

  if (isError || !protocol) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-6">
        <div className="w-full max-w-md">
          <EmptyState
            title="Протокол не найден"
            description="Ссылка недействительна или итоги больше не опубликованы. Попросите организатора прислать актуальную ссылку."
          />
        </div>
      </div>
    );
  }

  return <PublicProtocolTable protocol={protocol} />;
}

/** A published row paired with a key derived from its own content. */
interface KeyedRow {
  key: string;
  row: PublicProtocolRow;
}

/**
 * Give each row a stable key without an id.
 *
 * The backend sends no row ids to a public reader on purpose — a published protocol is a
 * document, not an API onto the entries behind it — so the key is built from the cells. Two
 * genuinely identical lines are disambiguated by an occurrence counter, which keeps the keys
 * unique without falling back to the array index.
 */
function keyRows(rows: readonly PublicProtocolRow[]): KeyedRow[] {
  const seen = new Map<string, number>();
  return rows.map((row) => {
    const content = row.cells.join("");
    const occurrence = (seen.get(content) ?? 0) + 1;
    seen.set(content, occurrence);
    return { key: `${content}#${occurrence}`, row };
  });
}

function PublicProtocolTable({ protocol }: { protocol: PublicProtocol }): React.JSX.Element {
  const heading = [protocol.competitionTitle, protocol.nomination].filter(Boolean).join(" · ");
  const publishedAt = formatPublishedAt(protocol.publishedAt);
  /** Which cell carries the award, so the winning lines can be set apart typographically. */
  const awardIndex = protocol.columns.findIndex((column) => column.key === "AWARD");
  const keyedRows = useMemo(() => keyRows(protocol.rows), [protocol.rows]);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8 md:px-6">
      <header className="flex flex-col gap-2">
        <p className="text-muted-foreground text-sm">{heading || APP_NAME}</p>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-semibold text-2xl text-foreground">{protocol.name}</h1>
          {/* Shown from the second publication on: a corrected protocol has to be visibly a
              correction, or a reader who saw the first version has no way to tell. */}
          {protocol.revision > 1 ? (
            <Badge variant="warning">Ревизия {protocol.revision}</Badge>
          ) : null}
        </div>
        {publishedAt ? (
          <p className="text-muted-foreground text-sm">Итоги опубликованы {publishedAt}</p>
        ) : null}
      </header>

      {protocol.rows.length === 0 ? (
        <EmptyState title="В протоколе нет строк" />
      ) : (
        <div className="scrollbar-custom overflow-x-auto rounded-lg border border-border">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">
              {`Протокол: ${protocol.name}${heading ? `. ${heading}` : ""}`}
            </caption>
            <thead>
              <tr className="border-border border-b bg-muted/40 text-left">
                {protocol.columns.map((column, columnIndex) => (
                  <th
                    key={column.key}
                    scope="col"
                    className={cn(
                      "px-3 py-2 font-medium",
                      // The award never wraps: "Лауреат I степени" broken over three lines is
                      // unreadable, and the table already scrolls sideways when it has to.
                      columnIndex === awardIndex && "whitespace-nowrap",
                    )}
                  >
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {keyedRows.map(({ key, row }) => (
                <tr
                  key={key}
                  className={cn(
                    "border-border border-b last:border-b-0",
                    row.award === "GRAND_PRIX" && "bg-primary/5",
                  )}
                >
                  {protocol.columns.map((column, columnIndex) => {
                    // Driven by the columns rather than the cells: the two are aligned by
                    // contract, and iterating the columns is what gives every cell a key that
                    // means something.
                    const cell = row.cells[columnIndex] ?? "";
                    return (
                      <td
                        key={`${key}-${column.key}`}
                        className={cn(
                          "px-3 py-2 align-top",
                          columnIndex === awardIndex && "whitespace-nowrap",
                          columnIndex === awardIndex &&
                            cell !== "" &&
                            "font-medium text-foreground",
                        )}
                      >
                        {cell || <span className="text-muted-foreground">—</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-muted-foreground text-sm">
        Электронные дипломы доступны участникам в личном кабинете, в разделе «Мои документы».
      </p>
    </div>
  );
}
