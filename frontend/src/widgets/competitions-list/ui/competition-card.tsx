import { ExternalLink, Medal } from "lucide-react";
import { Link } from "react-router";
import {
  competitionStatusLabel,
  competitionStatusVariant,
  formatDateTime,
} from "@/features/competitions";
import type { CompetitionSummary } from "@/shared/api/generated/model-competitions";
import { ROUTES } from "@/shared/config";
import { Badge, Button, Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/shared/ui";

interface CompetitionCardProps {
  competition: CompetitionSummary;
}

export function CompetitionCard({ competition }: CompetitionCardProps): React.JSX.Element {
  const workspacePath = `${ROUTES.staffCompetitions}/${competition.id}`;

  return (
    <Card className="flex h-full flex-col shadow-none transition-colors hover:border-border/80">
      <CardHeader className="gap-4 pb-3">
        <div className="flex items-start gap-3">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-md border bg-muted/40 text-muted-foreground">
            <Medal className="size-5" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1 space-y-2">
            {/* Two lines rather than one nowrap line: festival names here run to
                60+ characters, and a single ellipsized line showed the first word
                and nothing that tells two of them apart. */}
            <CardTitle className="line-clamp-2 break-words text-base">
              <Link
                to={workspacePath}
                className="outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
              >
                {competition.title}
              </Link>
            </CardTitle>
            <div className="flex flex-wrap gap-2">
              <Badge variant={competitionStatusVariant(competition.status)} size="sm">
                {competitionStatusLabel(competition.status)}
              </Badge>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="grid gap-2 text-muted-foreground">
          <p>
            <span className="font-medium text-foreground">Сезон:</span> {competition.season}
          </p>
          {competition.description ? (
            <p className="line-clamp-2 break-words">
              <span className="font-medium text-foreground">Описание:</span>{" "}
              {competition.description}
            </p>
          ) : null}
          <p>
            <span className="font-medium text-foreground">Обновлён:</span>{" "}
            {formatDateTime(competition.updatedAt)}
          </p>
        </div>
      </CardContent>
      <CardFooter className="mt-auto flex flex-wrap gap-2 border-t pt-4">
        <Button asChild size="sm">
          <Link to={workspacePath}>
            Открыть
            <ExternalLink className="size-3.5" aria-hidden="true" />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
