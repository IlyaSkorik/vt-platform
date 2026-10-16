import { Plus, Trash2 } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { useCompetitionDetail, useCompetitionsList } from "@/features/competitions";
import {
  type CreateAssignmentPayload,
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

/**
 * Which level of the taxonomy an assignment is filed against.
 *
 * `GENRE` is the default every festival starts from — one design for the whole
 * genre. `NOMINATION` exists because a genre's nominations are often judged by
 * different juries: the signatures on the sheet differ, so the sheet does too.
 * A nomination's own template wins over its genre's; the genre's keeps covering
 * everything that does not name one.
 */
type AssignmentLevel = "GENRE" | "NOMINATION";

const LEVEL_OPTIONS: SelectOption[] = [
  { value: "GENRE", label: "Весь жанр" },
  { value: "NOMINATION", label: "Отдельные номинации" },
];

/** One assignable target — a genre, or a nomination inside one. */
interface FreeTarget {
  id: string;
  name: string;
}

/** Targets offered under a heading: the genre they belong to, or nothing. */
interface TargetGroup {
  key: string;
  label: string | null;
  items: FreeTarget[];
}

/**
 * Assign a template to genres (or single nominations) of the competition already
 * chosen in the section.
 *
 * The competition is the section's context rather than the dialog's first field: an
 * organizer works on one competition at a time, and picking it inside every dialog
 * made a form of four questions out of one — the same reason the generation page
 * asks for it once, up front.
 */
function CreateAssignmentDialog({ competitionId }: { competitionId: string }): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const [level, setLevel] = useState<AssignmentLevel>("GENRE");
  const [targetIds, setTargetIds] = useState<Set<string>>(new Set());
  const [documentType, setDocumentType] = useState<DocumentType>("DIPLOMA");
  const [templateId, setTemplateId] = useState("");

  const competitionDetailQuery = useCompetitionDetail(competitionId || undefined);
  const templatesQuery = useDiplomaTemplates();
  const assignmentsQuery = useDiplomaAssignments();
  const createAssignment = useCreateAssignmentMutation();

  /**
   * What this competition already has of this kind, split by level.
   *
   * Split rather than merged: a genre's default says nothing about whether one of
   * its nominations has a template of its own, and that is exactly the combination
   * this dialog exists to create.
   */
  const taken = useMemo(() => {
    const genres = new Set<string>();
    const nominations = new Set<string>();
    for (const item of assignmentsQuery.data ?? []) {
      if (item.competitionId !== competitionId || item.documentType !== documentType) {
        continue;
      }
      if (item.disciplineId) {
        nominations.add(item.disciplineId);
      } else {
        genres.add(item.categoryId);
      }
    }
    return { genres, nominations };
  }, [assignmentsQuery.data, competitionId, documentType]);

  /**
   * The targets whose slot of this kind is still empty.
   *
   * An assigned target is left out rather than shown and rejected: the slot is
   * already taken, so offering it could only produce a conflict. Its diploma slot
   * being full says nothing about its thank-you slot, hence the filter is per kind.
   */
  const groups: TargetGroup[] = useMemo(() => {
    const categories = competitionDetailQuery.data?.categories ?? [];
    if (level === "GENRE") {
      const items = categories
        .filter((category) => !taken.genres.has(category.id))
        .map((category) => ({ id: category.id, name: category.name }));
      return items.length > 0 ? [{ key: "all", label: null, items }] : [];
    }
    const disciplines = competitionDetailQuery.data?.disciplines ?? [];
    return categories
      .map((category) => ({
        key: category.id,
        // Named by its genre, because two festivals' «Соло» are different things
        // and so are two genres' — the heading is what tells them apart.
        label: category.name,
        items: disciplines
          .filter(
            (discipline) =>
              discipline.categoryId === category.id && !taken.nominations.has(discipline.id),
          )
          .map((discipline) => ({ id: discipline.id, name: discipline.name })),
      }))
      .filter((group) => group.items.length > 0);
  }, [competitionDetailQuery.data, level, taken]);

  const offered = useMemo(() => groups.flatMap((group) => group.items), [groups]);

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
    setLevel("GENRE");
    setTargetIds(new Set());
    setDocumentType("DIPLOMA");
    setTemplateId("");
  }

  function handleOpenChange(next: boolean): void {
    setOpen(next);
    if (!next) {
      reset();
    }
  }

  function toggleTarget(id: string, on: boolean): void {
    const next = new Set(targetIds);
    if (on) {
      next.add(id);
    } else {
      next.delete(id);
    }
    setTargetIds(next);
  }

  async function handleSubmit(): Promise<void> {
    const picked = [...targetIds];
    if (!competitionId || picked.length === 0 || !templateId) {
      return;
    }
    // One list or the other, never both: the dialog files one decision at a time,
    // and the level is what says which column the rows carry.
    const payload: CreateAssignmentPayload =
      level === "GENRE"
        ? { competitionId, categoryIds: picked, templateId }
        : { competitionId, disciplineIds: picked, templateId };
    try {
      await createAssignment.mutateAsync(payload);
      toast.success(
        picked.length === 1 ? "Назначение создано" : `Назначений создано: ${picked.length}`,
      );
      handleOpenChange(false);
    } catch (error) {
      if (error instanceof ApiError && error.isConflict) {
        // The picker hides assigned targets, so this means the list went stale —
        // nothing was created, and a refetch will show what changed.
        const slot = documentTypeConfig(documentType).slotLabel.toLocaleLowerCase("ru-RU");
        const subject = level === "GENRE" ? "жанров" : "номинаций";
        toast.error(`Для одной из ${subject} уже назначен ${slot}. Обновите список.`);
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
    Boolean(competitionId && targetIds.size > 0 && templateId) && !createAssignment.isPending;

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
          {/* The slot the assignment fills. A genre has one of each, so this
              chooses which of its slots is being set — and therefore which
              targets are still free below. */}
          <Select
            label="Тип документа"
            required
            options={DOCUMENT_TYPE_OPTIONS}
            value={documentType}
            onValueChange={(value) => {
              setDocumentType(value as DocumentType);
              // A template of the previous kind cannot fill this slot, and the free
              // targets differ per kind.
              setTemplateId("");
              setTargetIds(new Set());
            }}
          />
          <Select
            label="Кому назначить"
            required
            options={LEVEL_OPTIONS}
            value={level}
            description="Шаблон номинации применяется вместо шаблона её жанра — например, когда номинации судит отдельное жюри."
            onValueChange={(value) => {
              setLevel(value as AssignmentLevel);
              // Genre ids and nomination ids are different things; carrying a
              // selection across the switch could only submit the wrong one.
              setTargetIds(new Set());
            }}
          />
          <TargetPicker
            level={level}
            groups={groups}
            selected={targetIds}
            competitionChosen={Boolean(competitionId)}
            loading={competitionDetailQuery.isLoading || assignmentsQuery.isLoading}
            slotLabel={documentTypeConfig(documentType).slotLabel.toLocaleLowerCase("ru-RU")}
            onToggle={toggleTarget}
            onToggleAll={(on) =>
              setTargetIds(on ? new Set(offered.map((item) => item.id)) : new Set())
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
 * Pick any number of genres — or of nominations, grouped by their genre — to
 * assign the template to.
 *
 * A checkbox list rather than a select: the whole point is seeing which targets
 * are still free and ticking several, which a single-value control cannot express.
 */
function TargetPicker({
  level,
  groups,
  selected,
  competitionChosen,
  loading,
  slotLabel,
  onToggle,
  onToggleAll,
}: {
  level: AssignmentLevel;
  groups: TargetGroup[];
  selected: Set<string>;
  competitionChosen: boolean;
  loading: boolean;
  slotLabel: string;
  onToggle: (id: string, on: boolean) => void;
  onToggleAll: (on: boolean) => void;
}): React.JSX.Element {
  const items = groups.flatMap((group) => group.items);
  const allSelected = items.length > 0 && items.every((item) => selected.has(item.id));
  const genres = level === "GENRE";

  return (
    <fieldset className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-2">
        <legend className="font-medium text-foreground text-sm">
          {genres ? "Жанры" : "Номинации"}
          <span className="ml-0.5 text-danger" aria-hidden="true">
            *
          </span>
        </legend>
        {items.length > 1 ? (
          <Button variant="ghost" size="sm" onClick={() => onToggleAll(!allSelected)}>
            {allSelected ? "Снять все" : "Выбрать все"}
          </Button>
        ) : null}
      </div>

      {!competitionChosen ? (
        <p className="text-muted-foreground text-sm">Сначала выберите фестиваль.</p>
      ) : loading ? (
        <p className="text-muted-foreground text-sm">
          {genres ? "Загружаем жанры…" : "Загружаем номинации…"}
        </p>
      ) : items.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          {genres
            ? `У каждого жанра этого фестиваля уже назначен ${slotLabel}. Освободите слот, удалив назначение в таблице.`
            : `У каждой номинации этого фестиваля уже назначен свой ${slotLabel} — или номинаций ещё нет. Их заводят в разделе «Жанры и номинации».`}
        </p>
      ) : (
        <div className="flex max-h-56 flex-col gap-3 overflow-y-auto rounded-lg border border-border p-3">
          {groups.map((group) => (
            <div key={group.key} className="flex flex-col gap-2">
              {group.label ? (
                <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">
                  {group.label}
                </p>
              ) : null}
              {group.items.map((item) => (
                <Checkbox
                  key={item.id}
                  label={item.name}
                  checked={selected.has(item.id)}
                  onCheckedChange={(checked) => onToggle(item.id, checked === true)}
                />
              ))}
            </div>
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
        header: "Жанр",
        cell: ({ row }) => row.original.nomination ?? "—",
      },
      {
        accessorKey: "discipline",
        header: "Номинация",
        // An assignment with no nomination covers the whole genre — which is what
        // it meant before nominations could carry one, so it is said plainly rather
        // than left as a dash the organizer has to interpret.
        cell: ({ row }) =>
          row.original.disciplineId ? (
            (row.original.discipline ?? "—")
          ) : (
            <span className="text-muted-foreground">Все номинации</span>
          ),
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
              aria-label={
                row.original.disciplineId
                  ? `Удалить назначение для номинации ${row.original.discipline ?? ""}`
                  : `Удалить назначение для жанра ${row.original.nomination ?? ""}`
              }
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
          label="Фестиваль"
          placeholder="Выберите фестиваль"
          options={competitionOptions}
          value={competitionId}
          onValueChange={setCompetitionId}
          disabled={competitionsQuery.isLoading}
        />
      </div>

      {!competitionId ? (
        <p className="text-muted-foreground text-sm">
          Выберите фестиваль, чтобы увидеть его назначения и связать шаблоны с жанрами.
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-2">
            <p className="text-muted-foreground text-sm">
              У каждого жанра свой шаблон диплома и шаблон благодарности. Отдельной номинации можно
              назначить свой шаблон — он применяется вместо шаблона жанра, например когда номинацию
              судит другое жюри.
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
                description="Создайте первое назначение, чтобы связать шаблон с жанром или номинацией этого фестиваля."
              />
            }
          />
        </div>
      )}
    </div>
  );
}
