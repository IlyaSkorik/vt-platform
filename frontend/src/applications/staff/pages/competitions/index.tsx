import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
  type CompetitionSortOption,
  type CompetitionStatusFilter,
  defaultSeason,
  filterAndSortCompetitions,
  resolveOrganizerId,
  useArchiveCompetitionMutation,
  useCompetitionsList,
  useCreateCompetitionMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import { ROUTES } from "@/shared/config";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
  const archiveCompetition = useArchiveCompetitionMutation();

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<CompetitionStatusFilter>("ALL");
  const [sort, setSort] = useState<CompetitionSortOption>("NEWEST");
  const [archiveTargetId, setArchiveTargetId] = useState<string | null>(null);

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
        title: "Новый конкурс",
        season: defaultSeason(),
      });
      toast.success("Черновик конкурса создан");
      navigate(`${ROUTES.staffCompetitions}/${created.id}`);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? (error.problem?.detail ?? "Не удалось создать конкурс")
          : "Не удалось создать конкурс";
      toast.error(message);
    }
  };

  const confirmArchive = async (): Promise<void> => {
    if (!archiveTargetId) {
      return;
    }
    try {
      await archiveCompetition.mutateAsync(archiveTargetId);
      toast.success("Конкурс архивирован");
      setArchiveTargetId(null);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? (error.problem?.detail ?? "Не удалось архивировать конкурс")
          : "Не удалось архивировать конкурс";
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
              Создать конкурс
            </Button>
          </PageActions>
        }
      >
        <PageTitle>Конкурсы</PageTitle>
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
              <CompetitionsGrid
                competitions={filteredCompetitions}
                onArchive={setArchiveTargetId}
                archivingId={archiveCompetition.isPending ? archiveTargetId : null}
              />
            )}
          </>
        ) : null}
      </PageContent>

      <Dialog
        open={archiveTargetId != null}
        onOpenChange={(open) => !open && setArchiveTargetId(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Архивировать конкурс?</DialogTitle>
            <DialogDescription>
              Архивированный конкурс станет только для чтения и скроется из активных операций.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setArchiveTargetId(null)}>
              Отмена
            </Button>
            <Button
              variant="danger"
              loading={archiveCompetition.isPending}
              onClick={() => void confirmArchive()}
            >
              Архивировать
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
