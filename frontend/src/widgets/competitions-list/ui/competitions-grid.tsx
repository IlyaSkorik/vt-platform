import type { CompetitionSummary } from "@/shared/api/generated/model-competitions";
import { CompetitionCard } from "./competition-card";

interface CompetitionsGridProps {
  competitions: readonly CompetitionSummary[];
}

export function CompetitionsGrid({ competitions }: CompetitionsGridProps): React.JSX.Element {
  return (
    // `grid-cols-1` rather than a bare `grid`: an implicit track is sized
    // `auto` and so takes the widest card's min-content, which a long title
    // pushed well past the screen — the single-column list measured 757px on a
    // phone and every card was cut off. The named breakpoints resolve to
    // `minmax(0, 1fr)` and never had the problem.
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
      {competitions.map((competition) => (
        <CompetitionCard key={competition.id} competition={competition} />
      ))}
    </div>
  );
}
