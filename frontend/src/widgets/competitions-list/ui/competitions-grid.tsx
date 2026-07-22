import type { CompetitionSummary } from "@/shared/api/generated/model-competitions";
import { CompetitionCard } from "./competition-card";

interface CompetitionsGridProps {
  competitions: readonly CompetitionSummary[];
}

export function CompetitionsGrid({ competitions }: CompetitionsGridProps): React.JSX.Element {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {competitions.map((competition) => (
        <CompetitionCard key={competition.id} competition={competition} />
      ))}
    </div>
  );
}
