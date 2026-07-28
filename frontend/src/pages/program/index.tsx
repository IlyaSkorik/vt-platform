import { useParams } from "react-router";

import { type PublicProgramRow, usePublicProgram } from "@/features/public-program";
import { APP_NAME } from "@/shared/config";
import { formatClock, formatSpan } from "@/shared/lib";
import { EmptyState, LoadingState } from "@/shared/ui";

/**
 * `/program/:slug` — a published programme, as handed to a sound engineer, a host, the
 * jury, or a display beside the stage.
 *
 * Unauthenticated by design: the slug in the URL is the only input and the only
 * credential. The page renders whatever columns the organizer published — it does not
 * know or care which ones those are, which is exactly why an unpublished column cannot
 * appear here. Type is sized to be read from several metres away, and the table scrolls
 * inside itself so the page never scrolls sideways on a phone.
 */
export function PublicProgramPage(): React.JSX.Element {
  const { slug } = useParams();
  const { data: program, isLoading, isError } = usePublicProgram(slug);

  if (isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-6">
        <LoadingState label="Загружаем программу…" />
      </div>
    );
  }

  if (isError || !program) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-6">
        <div className="w-full max-w-md">
          <EmptyState
            title="Программа не найдена"
            description="Ссылка недействительна или программа больше не опубликована. Попросите организатора прислать актуальную ссылку."
          />
        </div>
      </div>
    );
  }

  const heading = [program.competitionTitle, program.nomination].filter(Boolean).join(" · ");

  return (
    <div className="min-h-svh bg-background">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6 md:py-12">
        <header className="space-y-2">
          {heading ? (
            <p className="font-medium text-muted-foreground text-xs uppercase tracking-[0.18em]">
              {heading}
            </p>
          ) : null}
          <h1 className="font-bold text-3xl text-foreground tracking-tight sm:text-4xl">
            {program.name}
          </h1>
          <p className="text-muted-foreground text-sm">
            {program.rows.length > 0
              ? `Пунктов: ${program.rows.length} · Продолжительность: ${formatSpan(program.totalSeconds)}`
              : "Пока ни один пункт не опубликован"}
            {program.startsAt ? ` · Начало: ${formatClock(program.startsAt)}` : ""}
          </p>
        </header>

        {program.rows.length === 0 ? (
          <EmptyState
            title="Программа пуста"
            description="Организатор ещё не добавил пункты в эту программу."
          />
        ) : (
          <div className="scrollbar-custom overflow-x-auto rounded-lg border border-border">
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">{program.name}</caption>
              <thead>
                <tr className="border-border border-b bg-muted/50">
                  {program.columns.map((column) => (
                    <th
                      key={column.key}
                      scope="col"
                      className="whitespace-nowrap px-3 py-2.5 font-medium text-muted-foreground text-xs uppercase tracking-wide"
                    >
                      {column.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {program.rows.map((row) => (
                  <ProgramTableRow
                    // A public row carries no id by design, so its own published content
                    // is its identity. Safe here: the table is read-only and its rows
                    // never move, so nothing depends on the key surviving a reorder.
                    key={`${row.kind}${row.cells.join("")}`}
                    row={row}
                    columns={program.columns.map((column) => column.key)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        <footer className="pt-4 text-center text-muted-foreground text-xs">
          Программа обновляется автоматически · «{APP_NAME}»
        </footer>
      </div>
    </div>
  );
}

function ProgramTableRow({
  row,
  columns,
}: {
  row: PublicProgramRow;
  columns: string[];
}): React.JSX.Element {
  const isPerformance = row.kind === "PERFORMANCE";
  return (
    <tr
      className={
        isPerformance
          ? "border-border border-b last:border-0"
          : "border-border border-b bg-muted/40 last:border-0"
      }
    >
      {row.cells.map((cell, index) => {
        const column = columns[index];
        const emphasise = column === "TIME" || (column === "TITLE" && !isPerformance);
        return (
          <td
            // Cells are positional against `columns`, so the column key identifies them.
            key={column ?? String(index)}
            className={
              emphasise
                ? "whitespace-nowrap px-3 py-3 font-semibold text-base tabular-nums"
                : "px-3 py-3 text-sm"
            }
          >
            {cell || <span className="text-muted-foreground">—</span>}
          </td>
        );
      })}
    </tr>
  );
}
