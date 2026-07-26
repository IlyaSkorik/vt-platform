import { Plus, Trash2 } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { useCompetitionDetail, useCompetitionsList } from "@/features/competitions";
import {
  type DiplomaAssignment,
  DOCUMENT_TYPE_OPTIONS,
  type DocumentType,
  documentTypeConfig,
  useCreateAssignmentMutation,
  useDeleteAssignmentMutation,
  useDiplomaAssignments,
  useDiplomaTemplates,
} from "@/features/diplomas";
import { ApiError } from "@/shared/api";
import {
  Badge,
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
  const [documentType, setDocumentType] = useState<DocumentType>("DIPLOMA");
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
  // Only templates of the chosen kind can fill that slot — the backend derives the
  // slot from the template's own type, so offering the others would be a trap.
  const templateOptions: SelectOption[] = useMemo(
    () =>
      (templatesQuery.data ?? [])
        .filter((template) => template.type === documentType)
        .map((template) => ({ value: template.id, label: template.name })),
    [templatesQuery.data, documentType],
  );

  function reset(): void {
    setCompetitionId("");
    setCategoryId("");
    setDocumentType("DIPLOMA");
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
        // Per kind: a diploma assignment does not block a thank-you assignment.
        const slot = documentTypeConfig(documentType).slotLabel.toLocaleLowerCase("ru-RU");
        toast.error(`Для этой номинации уже назначен ${slot}.`);
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
          {/* The slot the assignment fills. A nomination has one of each, so this
              chooses which of its slots is being set. */}
          <Select
            label="Тип документа"
            required
            options={DOCUMENT_TYPE_OPTIONS}
            value={documentType}
            onValueChange={(value) => {
              setDocumentType(value as DocumentType);
              // A template of the previous kind cannot fill this slot.
              setTemplateId("");
            }}
          />
          <Select
            label={documentTypeConfig(documentType).slotLabel}
            required
            placeholder={
              templateOptions.length > 0
                ? "Выберите шаблон"
                : `Нет шаблонов типа «${documentTypeConfig(documentType).label}»`
            }
            options={templateOptions}
            value={templateId}
            onValueChange={setTemplateId}
            disabled={templateOptions.length === 0}
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
        accessorKey: "documentType",
        header: "Тип документа",
        cell: ({ row }) => {
          const kind = documentTypeConfig(row.original.documentType);
          return (
            <Badge variant={kind.tone} size="sm">
              {kind.label}
            </Badge>
          );
        },
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
          Каждая номинация имеет отдельный шаблон диплома и шаблон благодарности — так у разных
          номинаций могут быть разные дизайны.
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
