import { useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router";
import {
  defaultSeason,
  resolveOrganizerId,
  useCompetitionsList,
  useCreateCompetitionMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import { ROUTES } from "@/shared/config";
import {
  Button,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  Skeleton,
  toast,
} from "@/shared/ui";

export function StaffCreateCompetitionPage(): React.JSX.Element {
  const navigate = useNavigate();
  const started = useRef(false);
  const competitionsQuery = useCompetitionsList();
  const createCompetition = useCreateCompetitionMutation();

  useEffect(() => {
    if (started.current || competitionsQuery.isLoading) {
      return;
    }
    started.current = true;

    void (async () => {
      const organizerId = resolveOrganizerId(competitionsQuery.data ?? []);

      try {
        const created = await createCompetition.mutateAsync({
          organizerId,
          title: "Новый фестиваль",
          season: defaultSeason(),
        });
        navigate(`${ROUTES.staffCompetitions}/${created.id}`, { replace: true });
      } catch (error) {
        const message =
          error instanceof ApiError
            ? (error.problem?.detail ?? "Не удалось создать фестиваль")
            : "Не удалось создать фестиваль";
        toast.error(message);
      }
    })();
  }, [competitionsQuery.data, competitionsQuery.isLoading, createCompetition, navigate]);

  return (
    <PageContainer size="narrow">
      <PageHeader>
        <PageTitle>Создание фестиваля</PageTitle>
        <PageDescription>Создаём черновик и открываем рабочее пространство…</PageDescription>
      </PageHeader>
      <PageContent className="space-y-4">
        <div role="status" aria-label="Создание фестиваля" className="space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
        {createCompetition.isError ? (
          <Button asChild variant="outline">
            <Link to={ROUTES.staffCompetitions}>К списку фестивалей</Link>
          </Button>
        ) : null}
      </PageContent>
    </PageContainer>
  );
}
