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
  Checkbox,
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

/** A nomination offered for assignment, with the name the organizer knows it by. */
interface FreeNomination {
  id: string;
  name: string;
}

/**
 * Assign a template to nominations of the competition already chosen in the section.
 *
 * The competition is the section's context rather than the dialog's first field: an
 * organizer works on one competition at a time, and picking it inside every dialog
 * made a form of four questions out of one — the same reason the generation page
 * asks for it once, up front.
 */
function CreateAssignmentDialog({ competitionId }: { competitionId: string }): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const [categoryIds, setCategoryIds] = useState<Set<string>>(new Set());
  const [documentType, setDocumentType] = useState<DocumentType>("DIPLOMA");
  const [templateId, setTemplateId] = useState("");

  const competitionDetailQuery = useCompetitionDetail(competitionId || undefined);
  const templatesQuery = useDiplomaTemplates();
  const assignmentsQuery = useDiplomaAssignments();
  const createAssignment = useCreateAssignmentMutation();

  /**
   * The nominations whose slot of this kind is still empty.
   *
   * An assigned nomination is left out rather than shown and rejected: the slot is
   * already taken, so offering it could only produce a conflict. Its diploma slot
   * being full says nothing about its thank-you slot, hence the filter is per kind.
   */
  const freeNominations: FreeNomination[] = useMemo(() => {
    const taken = new Set(
      (assignmentsQuery.data ?? [])
        .filter(
          (item) => item.competitionId === competitionId && item.documentType === documentType,
        )
        .map((item) => item.categoryId),
    );
    return (competitionDetailQuery.data?.categories ?? [])
      .filter((category) => !taken.has(category.id))
      .map((category) => ({ id: category.id, name: category.name }));
  }, [assignmentsQuery.data, competitionDetailQuery.data, competitionId, documentType]);

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
    // The competition is not reset: it belongs to the section, and an organizer who
    // just assigned a diploma template usually assigns the thank-you one next.
    setCategoryIds(new Set());
    setDocumentType("DIPLOMA");
    setTemplateId("");
  }

  function handleOpenChange(next: boolean): void {
    setOpen(next);
    if (!next) {
      reset();
    }
  }

  function toggleNomination(id: string, on: boolean): void {
    const next = new Set(categoryIds);
    if (on) {
      next.add(id);
    } else {
      next.delete(id);
    }
    setCategoryIds(next);
  }

  async function handleSubmit(): Promise<void> {
    const picked = [...categoryIds];
    if (!competitionId || picked.length === 0 || !templateId) {
      return;
    }
    try {
      await createAssignment.mutateAsync({
        competitionId,
        categoryIds: picked,
        templateId,
      });
      toast.success(
        picked.length === 1 ? "Назначение создано" : `Назначений создано: ${picked.length}`,
      );
      handleOpenChange(false);
    } catch (error) {
      if (error instanceof ApiError && error.isConflict) {
        // The picker hides assigned nominations, so this means the list went stale —
        // nothing was created, and a refetch will show what changed.
        const slot = documentTypeConfig(documentType).slotLabel.toLocaleLowerCase("ru-RU");
        toast.error(`Для одной из номинаций уже назначен ${slot}. Обновите список.`);
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
    Boolean(competitionId && categoryIds.size > 0 && templateId) && !createAssignment.isPending;

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
          {/* The slot the assignment fills. A nomination has one of each, so this
              chooses which of its slots is being set — and therefore which
              nominations are still free below. */}
          <Select
            label="Тип документа"
            required
            options={DOCUMENT_TYPE_OPTIONS}
            value={documentType}
            onValueChange={(value) => {
              setDocumentType(value as DocumentType);
              // A template of the previous kind cannot fill this slot, and the free
              // nominations differ per kind.
              setTemplateId("");
              setCategoryIds(new Set());
            }}
          />
          <NominationPicker
            nominations={freeNominations}
            selected={categoryIds}
            competitionChosen={Boolean(competitionId)}
            loading={competitionDetailQuery.isLoading || assignmentsQuery.isLoading}
            slotLabel={documentTypeConfig(documentType).slotLabel.toLocaleLowerCase("ru-RU")}
            onToggle={toggleNomination}
            onToggleAll={(on) =>
              setCategoryIds(on ? new Set(freeNominations.map((item) => item.id)) : new Set())
            }
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

/**
 * Pick any number of nominations to assign the template to.
 *
 * A checkbox list rather than a select: the whole point is seeing which
 * nominations are still free and ticking several, which a single-value control
 * cannot express.
 */
function NominationPicker({
  nominations,
  selected,
  competitionChosen,
  loading,
  slotLabel,
  onToggle,
  onToggleAll,
}: {
  nominations: FreeNomination[];
  selected: Set<string>;
  competitionChosen: boolean;
  loading: boolean;
  slotLabel: string;
  onToggle: (id: string, on: boolean) => void;
  onToggleAll: (on: boolean) => void;
}): React.JSX.Element {
  const allSelected = nominations.length > 0 && nominations.every((item) => selected.has(item.id));

  return (
    <fieldset className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-2">
        <legend className="font-medium text-foreground text-sm">
          Номинации
          <span className="ml-0.5 text-danger" aria-hidden="true">
            *
          </span>
        </legend>
        {nominations.length > 1 ? (
          <Button variant="ghost" size="sm" onClick={() => onToggleAll(!allSelected)}>
            {allSelected ? "Снять все" : "Выбрать все"}
          </Button>
        ) : null}
      </div>

      {!competitionChosen ? (
        <p className="text-muted-foreground text-sm">Сначала выберите конкурс.</p>
      ) : loading ? (
        <p className="text-muted-foreground text-sm">Загружаем номинации…</p>
      ) : nominations.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          У каждой номинации этого конкурса уже назначен {slotLabel}. Освободите слот, удалив
          назначение в таблице.
        </p>
      ) : (
        <div className="flex max-h-56 flex-col gap-2 overflow-y-auto rounded-lg border border-border p-3">
          {nominations.map((nomination) => (
            <Checkbox
              key={nomination.id}
              label={nomination.name}
              checked={selected.has(nomination.id)}
              onCheckedChange={(checked) => onToggle(nomination.id, checked === true)}
            />
          ))}
        </div>
      )}

      {selected.size > 0 ? (
        <p className="text-muted-foreground text-sm">Выбрано: {selected.size}</p>
      ) : null}
    </fieldset>
  );
}

export function AssignmentsSection(): React.JSX.Element {
  const [competitionId, setCompetitionId] = useState("");

  const competitionsQuery = useCompetitionsList();
  const assignmentsQuery = useDiplomaAssignments();
  const deleteAssignment = useDeleteAssignmentMutation();

  const competitionOptions: SelectOption[] = useMemo(
    () => (competitionsQuery.data ?? []).map((item) => ({ value: item.id, label: item.title })),
    [competitionsQuery.data],
  );

  // Assignments belong to a competition, so the section shows one competition's —
  // the whole list across competitions is a report nobody asked for, and it made
  // "which template does «Вокал» use?" a search rather than a glance.
  const assignments: DiplomaAssignment[] = useMemo(
    () => (assignmentsQuery.data ?? []).filter((item) => item.competitionId === competitionId),
    [assignmentsQuery.data, competitionId],
  );

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
    <div className="flex flex-col gap-6">
      <div className="max-w-md">
        <Select
          label="Конкурс"
          placeholder="Выберите конкурс"
          options={competitionOptions}
          value={competitionId}
          onValueChange={setCompetitionId}
          disabled={competitionsQuery.isLoading}
        />
      </div>

      {!competitionId ? (
        <p className="text-muted-foreground text-sm">
          Выберите конкурс, чтобы увидеть его назначения и связать шаблоны с номинациями.
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-2">
            <p className="text-muted-foreground text-sm">
              Каждая номинация имеет отдельный шаблон диплома и шаблон благодарности — так у разных
              номинаций могут быть разные дизайны.
            </p>
            <CreateAssignmentDialog competitionId={competitionId} />
          </div>
          <DataTable
            columns={columns}
            data={assignments}
            loading={assignmentsQuery.isLoading}
            emptyContent={
              <EmptyState
                title="Назначений пока нет"
                description="Создайте первое назначение, чтобы связать шаблон с номинацией этого конкурса."
              />
            }
          />
        </div>
      )}
    </div>
  );
}
