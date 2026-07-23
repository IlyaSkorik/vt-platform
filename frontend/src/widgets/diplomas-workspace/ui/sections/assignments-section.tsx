import { Plus, Trash2 } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { useCompetitionDetail, useCompetitionsList } from "@/features/competitions";
import {
  type DiplomaAssignment,
  useCreateAssignmentMutation,
  useDeleteAssignmentMutation,
  useDiplomaAssignments,
  useDiplomaTemplates,
} from "@/features/diplomas";
import { ApiError } from "@/shared/api";
import {
  Button,
  type ColumnDef,
  DataTable,
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  EmptyState,
  Select,
  type SelectOption,
  toast,
} from "@/shared/ui";
import { formatDate } from "../../lib/format";

function CreateAssignmentDialog(): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const [competitionId, setCompetitionId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [templateId, setTemplateId] = useState("");

  const competitionsQuery = useCompetitionsList();
  const competitionDetailQuery = useCompetitionDetail(competitionId || undefined);
  const templatesQuery = useDiplomaTemplates();
  const createAssignment = useCreateAssignmentMutation();

  const competitionOptions: SelectOption[] = useMemo(
    () => (competitionsQuery.data ?? []).map((item) => ({ value: item.id, label: item.title })),
    [competitionsQuery.data],
  );
  const nominationOptions: SelectOption[] = useMemo(
    () =>
      (competitionDetailQuery.data?.categories ?? []).map((category) => ({
        value: category.id,
        label: category.name,
      })),
    [competitionDetailQuery.data],
  );
  const templateOptions: SelectOption[] = useMemo(
    () =>
      (templatesQuery.data ?? []).map((template) => ({
        value: template.id,
        label: template.name,
      })),
    [templatesQuery.data],
  );

  function reset(): void {
    setCompetitionId("");
    setCategoryId("");
    setTemplateId("");
  }

  function handleOpenChange(next: boolean): void {
    setOpen(next);
    if (!next) {
      reset();
    }
  }

  async function handleSubmit(): Promise<void> {
    if (!competitionId || !categoryId || !templateId) {
      return;
    }
    try {
      await createAssignment.mutateAsync({ competitionId, categoryId, templateId });
      toast.success("Назначение создано");
      handleOpenChange(false);
    } catch (error) {
      if (error instanceof ApiError && error.isConflict) {
        toast.error("Для этой номинации уже назначен шаблон.");
        return;
      }
      const message =
        error instanceof ApiError
          ? (error.problem?.detail ?? "Не удалось создать назначение.")
          : "Не удалось создать назначение.";
      toast.error(message);
    }
  }

  const canSubmit =
    Boolean(competitionId && categoryId && templateId) && !createAssignment.isPending;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="size-4" aria-hidden="true" />
          Создать назначение
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Новое назначение</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <Select
            label="Конкурс"
            required
            placeholder="Выберите конкурс"
            options={competitionOptions}
            value={competitionId}
            onValueChange={(value) => {
              setCompetitionId(value);
              setCategoryId("");
            }}
          />
          <Select
            label="Номинация"
            required
            placeholder={competitionId ? "Выберите номинацию" : "Сначала выберите конкурс"}
            options={nominationOptions}
            value={categoryId}
            onValueChange={setCategoryId}
            disabled={!competitionId || competitionDetailQuery.isLoading}
          />
          <Select
            label="Шаблон"
            required
            placeholder="Выберите шаблон"
            options={templateOptions}
            value={templateId}
            onValueChange={setTemplateId}
          />
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Отмена</Button>
          </DialogClose>
          <Button onClick={() => void handleSubmit()} disabled={!canSubmit}>
            Создать
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function AssignmentsSection(): React.JSX.Element {
  const assignmentsQuery = useDiplomaAssignments();
  const deleteAssignment = useDeleteAssignmentMutation();

  const handleDelete = useCallback(
    async (assignment: DiplomaAssignment): Promise<void> => {
      try {
        await deleteAssignment.mutateAsync(assignment.id);
        toast.success("Назначение удалено");
      } catch (error) {
        const message =
          error instanceof ApiError
            ? (error.problem?.detail ?? "Не удалось удалить назначение.")
            : "Не удалось удалить назначение.";
        toast.error(message);
      }
    },
    [deleteAssignment],
  );

  const columns: ColumnDef<DiplomaAssignment>[] = useMemo(
    () => [
      {
        accessorKey: "competition",
        header: "Конкурс",
        cell: ({ row }) => row.original.competition ?? "—",
      },
      {
        accessorKey: "nomination",
        header: "Номинация",
        cell: ({ row }) => row.original.nomination ?? "—",
      },
      {
        accessorKey: "templateName",
        header: "Шаблон",
        cell: ({ row }) => (
          <div className="flex items-center gap-2">
            <span>{row.original.templateName}</span>
          </div>
        ),
      },
      {
        id: "created",
        header: "Создано",
        cell: ({ row }) => (
          <span className="text-muted-foreground">{formatDate(row.original.createdAt)}</span>
        ),
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <div className="flex justify-end">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void handleDelete(row.original)}
              disabled={deleteAssignment.isPending}
              aria-label={`Удалить назначение для номинации ${row.original.nomination ?? ""}`}
            >
              <Trash2 className="size-4" aria-hidden="true" />
            </Button>
          </div>
        ),
      },
    ],
    [deleteAssignment.isPending, handleDelete],
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-muted-foreground text-sm">
          Здесь задаётся, какой шаблон используется для конкретного конкурса и номинации.
        </p>
        <CreateAssignmentDialog />
      </div>
      <DataTable
        columns={columns}
        data={assignmentsQuery.data ?? []}
        loading={assignmentsQuery.isLoading}
        emptyContent={
          <EmptyState
            title="Назначений пока нет"
            description="Создайте первое назначение, чтобы связать шаблон с конкурсом и номинацией."
          />
        }
      />
    </div>
  );
}
