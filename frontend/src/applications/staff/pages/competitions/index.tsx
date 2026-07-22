import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
  type CompetitionSortOption,
  type CompetitionStatusFilter,
  defaultSeason,
  filterAndSortCompetitions,
  resolveOrganizerId,
  useCompetitionsList,
  useCreateCompetitionMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import { ROUTES } from "@/shared/config";
import {
  Button,
  EmptyState,
  PageActions,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  toast,
} from "@/shared/ui";
import {
  CompetitionsEmptyState,
  CompetitionsErrorState,
  CompetitionsGrid,
  CompetitionsListSkeleton,
  CompetitionsToolbar,
} from "@/widgets/competitions-list";

export function StaffCompetitionsPage(): React.JSX.Element {
  const navigate = useNavigate();
  const competitionsQuery = useCompetitionsList();
  const createCompetition = useCreateCompetitionMutation();

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<CompetitionStatusFilter>("ALL");
  const [sort, setSort] = useState<CompetitionSortOption>("NEWEST");

  const competitions = competitionsQuery.data ?? [];

  const filteredCompetitions = useMemo(
    () => filterAndSortCompetitions(competitions, { search, status, sort }),
    [competitions, search, sort, status],
  );

  const handleCreate = async (): Promise<void> => {
    const organizerId = resolveOrganizerId(competitions);

    try {
      const created = await createCompetition.mutateAsync({
        organizerId,
        title: "Новый фестиваль",
        season: defaultSeason(),
      });
      toast.success("Черновик фестиваля создан");
      navigate(`${ROUTES.staffCompetitions}/${created.id}`);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? (error.problem?.detail ?? "Не удалось создать фестиваль")
          : "Не удалось создать фестиваль";
      toast.error(message);
    }
  };

  return (
    <PageContainer size="wide">
      <PageHeader
        actions={
          <PageActions>
            <Button
              onClick={() => void handleCreate()}
              loading={createCompetition.isPending}
              disabled={createCompetition.isPending}
              leftIcon={<Plus aria-hidden="true" />}
            >
              Создать фестиваль
            </Button>
          </PageActions>
        }
      >
        <PageTitle>Фестивали</PageTitle>
        <PageDescription>
          Управляйте черновиками, публикацией и регистрацией в одном рабочем пространстве.
        </PageDescription>
      </PageHeader>

      <PageContent>
        {competitionsQuery.isLoading ? <CompetitionsListSkeleton /> : null}

        {competitionsQuery.isError ? (
          <CompetitionsErrorState onRetry={() => void competitionsQuery.refetch()} />
        ) : null}

        {competitionsQuery.isSuccess ? (
          <>
            <CompetitionsToolbar
              search={search}
              status={status}
              sort={sort}
              onSearchChange={setSearch}
              onStatusChange={setStatus}
              onSortChange={setSort}
            />

            {competitions.length === 0 ? (
              <CompetitionsEmptyState
                onCreate={() => void handleCreate()}
                creating={createCompetition.isPending}
              />
            ) : filteredCompetitions.length === 0 ? (
              <EmptyState
                title="Ничего не найдено"
                description="Попробуйте изменить поиск или фильтры."
                action={
                  <Button
                    variant="outline"
                    onClick={() => {
                      setSearch("");
                      setStatus("ALL");
                    }}
                  >
                    Сбросить фильтры
                  </Button>
                }
              />
            ) : (
              <CompetitionsGrid competitions={filteredCompetitions} />
            )}
          </>
        ) : null}
      </PageContent>
    </PageContainer>
  );
}
