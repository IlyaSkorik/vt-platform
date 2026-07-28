import { useParams } from "react-router";

import { type PublicProgramItem, usePublicProgram } from "@/features/public-program";
import { APP_NAME } from "@/shared/config";
import { formatClock, formatDuration, formatSpan } from "@/shared/lib";
import { Alert, Badge, EmptyState, LoadingState } from "@/shared/ui";

/**
 * What a non-performance block is called on a public screen.
 *
 * Deliberately its own map rather than the constructor's: audience-facing wording is
 * free to differ from the organizer's vocabulary, and a public page has no business
 * depending on the organizer feature.
 */
const PUBLIC_KIND_LABELS: Record<string, string> = {
  BREAK: "Перерыв",
  OPENING: "Открытие",
  AWARD: "Награждение",
  MASTER_CLASS: "Мастер-класс",
  TECHNICAL: "Технический блок",
};

/**
 * `/program/:slug` — a published programme, as handed to a sound engineer, a host,
 * the jury, or a display beside the stage.
 *
 * Unauthenticated by design: the slug in the URL is the only input and the only
 * credential. The layout is deliberately full-bleed and large-type — one of its jobs
 * is to be legible on a screen several metres away — and the time column is the
 * anchor, because "when does my number start" is the one question every reader has.
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
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8 sm:px-6 md:py-12">
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
            {program.items.length > 0
              ? `Пунктов: ${program.items.length} · Продолжительность: ${formatSpan(program.totalSeconds)}`
              : "Пока ни один пункт не опубликован"}
            {program.startsAt ? ` · Начало: ${formatClock(program.startsAt)}` : ""}
          </p>
        </header>

        {program.items.length === 0 ? (
          <EmptyState
            title="Программа пуста"
            description="Организатор ещё не добавил пункты в эту программу."
          />
        ) : (
          <ol className="flex flex-col gap-2">
            {program.items.map((item) => (
              <ProgramLine key={`${item.position}-${item.title}`} item={item} />
            ))}
          </ol>
        )}

        <footer className="pt-4 text-center text-muted-foreground text-xs">
          Программа обновляется автоматически · «{APP_NAME}»
        </footer>
      </div>
    </div>
  );
}

function ProgramLine({ item }: { item: PublicProgramItem }): React.JSX.Element {
  const isPerformance = item.kind === "PERFORMANCE";
  return (
    <li
      className={
        isPerformance
          ? "flex flex-col gap-2 rounded-lg border border-border bg-card p-4 sm:flex-row sm:items-baseline sm:gap-5"
          : "flex flex-col gap-2 rounded-lg border border-border border-dashed bg-muted/40 p-4 sm:flex-row sm:items-baseline sm:gap-5"
      }
    >
      <div className="flex shrink-0 items-baseline gap-3 sm:w-32">
        <span className="font-semibold text-foreground text-xl tabular-nums sm:text-2xl">
          {formatClock(item.startsAt)}
        </span>
        <span className="text-muted-foreground text-xs tabular-nums">{item.position}</span>
      </div>

      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-baseline gap-2">
          <p className="font-medium text-foreground text-lg">{item.title}</p>
          {isPerformance ? null : (
            <Badge variant="secondary">{PUBLIC_KIND_LABELS[item.kind] ?? "Блок"}</Badge>
          )}
        </div>
        {item.performer ? (
          <p className="text-muted-foreground text-sm">
            {item.performer}
            {item.organization ? ` · ${item.organization}` : ""}
          </p>
        ) : null}
        {item.teachers.length > 0 ? (
          <p className="text-muted-foreground text-xs">Педагоги: {item.teachers.join(", ")}</p>
        ) : null}
        {item.note ? (
          <Alert variant="info" className="mt-2">
            {item.note}
          </Alert>
        ) : null}
      </div>

      <span className="shrink-0 text-muted-foreground text-sm tabular-nums">
        {formatDuration(item.durationSeconds)}
      </span>
    </li>
  );
}
