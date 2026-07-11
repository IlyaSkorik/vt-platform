import { Archive, ExternalLink, Medal } from "lucide-react";
import { Link } from "react-router";
import {
  competitionStatusLabel,
  competitionStatusVariant,
  formatDateTime,
  registrationStatusLabel,
} from "@/features/competitions";
import type { CompetitionSummary } from "@/shared/api/generated/model-competitions";
import { ROUTES } from "@/shared/config";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
  IconButton,
} from "@/shared/ui";

interface CompetitionCardProps {
  competition: CompetitionSummary;
  onArchive: (competitionId: string) => void;
  archiving?: boolean;
}

export function CompetitionCard({
  competition,
  onArchive,
  archiving = false,
}: CompetitionCardProps): React.JSX.Element {
  const workspacePath = `${ROUTES.staffCompetitions}/${competition.id}`;
  const isArchived = competition.status === "ARCHIVED";

  return (
    <Card className="flex h-full flex-col shadow-none transition-colors hover:border-border/80">
      <CardHeader className="gap-4 pb-3">
        <div className="flex items-start gap-3">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-md border bg-muted/40 text-muted-foreground">
            <Medal className="size-5" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1 space-y-2">
            <CardTitle className="truncate text-base">
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
              <Badge variant="outline" size="sm">
                Регистрация: {registrationStatusLabel(competition.status)}
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
            <p className="line-clamp-2">
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
        {!isArchived ? (
          <IconButton
            variant="ghost"
            size="sm"
            aria-label={`Архивировать ${competition.title}`}
            icon={<Archive aria-hidden="true" />}
            onClick={() => onArchive(competition.id)}
            disabled={archiving}
          />
        ) : null}
      </CardFooter>
    </Card>
  );
}
