import { FileSpreadsheet } from "lucide-react";
import { Link } from "react-router";

import { type PublishedProtocolLink, useCompetitionResults } from "@/features/public-protocol";
import { Badge, Button } from "@/shared/ui";

import { LandingSection } from "../landing-section";

const PUBLISHED_AT_FORMATTER = new Intl.DateTimeFormat("ru-RU", {
  day: "2-digit",
  month: "long",
  year: "numeric",
});

function formatPublishedAt(iso: string | null): string {
  if (!iso) {
    return "";
  }
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? "" : PUBLISHED_AT_FORMATTER.format(parsed);
}

function ResultRow({ protocol }: { protocol: PublishedProtocolLink }): React.JSX.Element {
  const publishedAt = formatPublishedAt(protocol.publishedAt);
  return (
    <li className="flex flex-col gap-3 rounded-lg border bg-card p-4 text-card-foreground shadow-elevation-1 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <FileSpreadsheet className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
        <div className="min-w-0 space-y-0.5">
          <p className="flex flex-wrap items-center gap-2 font-medium">
            {protocol.nomination ?? protocol.name}
            {/* From the second publication on: a corrected protocol has to look like a
                correction to somebody who already read the first one. */}
            {protocol.revision > 1 ? (
              <Badge variant="warning">Ревизия {protocol.revision}</Badge>
            ) : null}
          </p>
          <p className="text-muted-foreground text-sm">
            Протокол{publishedAt ? ` · опубликован ${publishedAt}` : ""}
          </p>
        </div>
      </div>
      <Button asChild variant="outline" size="sm" className="shrink-0">
        <Link to={protocol.path}>Смотреть протокол</Link>
      </Button>
    </li>
  );
}

interface ResultsSectionProps {
  festivalId: string;
}

/**
 * The "Результаты" section: one link per published protocol.
 *
 * Not a Landing Builder block, and deliberately so. Every other section on this page is
 * something the organizer chose to add; results are something they **published**, which is
 * already an explicit act with its own confirmation dialog. Requiring a second, separate act
 * to make them visible would mean a festival whose results are out there and whose page still
 * says nothing — so the section appears by itself the moment the first protocol is published,
 * and renders nothing before that.
 *
 * Links rather than contents: a landing page lists the documents a competition has published,
 * and each protocol decides for itself which columns it shows.
 */
export function ResultsSection({ festivalId }: ResultsSectionProps): React.JSX.Element | null {
  const { data: protocols } = useCompetitionResults(festivalId);

  // Also the failure path: an unreachable results endpoint must not put an empty heading on
  // an otherwise fine landing page.
  if (protocols == null || protocols.length === 0) {
    return null;
  }

  return (
    <LandingSection
      id="results"
      title="Результаты"
      subtitle="Итоги по номинациям. Участникам электронные дипломы доступны в личном кабинете."
    >
      <ul className="space-y-3">
        {protocols.map((protocol) => (
          <ResultRow key={protocol.slug} protocol={protocol} />
        ))}
      </ul>
    </LandingSection>
  );
}
