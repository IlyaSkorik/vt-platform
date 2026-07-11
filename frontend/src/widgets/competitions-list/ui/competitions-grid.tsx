import type { CompetitionSummary } from "@/shared/api/generated/model-competitions";
import { CompetitionCard } from "./competition-card";

interface CompetitionsGridProps {
  competitions: readonly CompetitionSummary[];
  onArchive: (competitionId: string) => void;
  archivingId?: string | null;
}

export function CompetitionsGrid({
  competitions,
  onArchive,
  archivingId = null,
}: CompetitionsGridProps): React.JSX.Element {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {competitions.map((competition) => (
        <CompetitionCard
          key={competition.id}
          competition={competition}
          onArchive={onArchive}
          archiving={archivingId === competition.id}
        />
      ))}
    </div>
  );
}
