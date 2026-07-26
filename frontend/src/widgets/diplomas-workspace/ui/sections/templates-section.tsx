import { LayoutTemplate, PenTool, Plus } from "lucide-react";
import { useState } from "react";
import { generatePath, Link } from "react-router";
import {
  type DiplomaTemplate,
  DOCUMENT_TYPE_OPTIONS,
  type DocumentType,
  documentTypeConfig,
  useCreateTemplateMutation,
  useDiplomaTemplates,
} from "@/features/diplomas";
import { ApiError } from "@/shared/api";
import { ROUTES } from "@/shared/config";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  EmptyState,
  Input,
  Select,
  Skeleton,
  Textarea,
  toast,
} from "@/shared/ui";
import { formatDate } from "../../lib/format";

const MAX_NAME_LENGTH = 160;

interface CreateTemplateDialogProps {
  /** Renders the trigger; `variant="outline"` for the empty-state call to action. */
  variant?: "primary" | "outline";
}

function CreateTemplateDialog({
  variant = "primary",
}: CreateTemplateDialogProps): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  // Defaults to the diploma: it is the kind an organizer reaches for most, and the
  // one every pre-existing template is.
  const [type, setType] = useState<DocumentType>("DIPLOMA");
  const createTemplate = useCreateTemplateMutation();

  function handleOpenChange(next: boolean): void {
    setOpen(next);
    if (!next) {
      setName("");
      setDescription("");
      setType("DIPLOMA");
    }
  }

  async function handleSubmit(): Promise<void> {
    const trimmed = name.trim();
    if (!trimmed) {
      return;
    }
    try {
      await createTemplate.mutateAsync({ name: trimmed, type, description: description.trim() });
      toast.success("Шаблон создан");
      handleOpenChange(false);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? (error.problem?.detail ?? "Не удалось создать шаблон.")
          : "Не удалось создать шаблон.";
      toast.error(message);
    }
  }

  const canSubmit = name.trim().length > 0 && !createTemplate.isPending;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant={variant}>
          <Plus className="size-4" aria-hidden="true" />
          Создать шаблон
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Новый шаблон</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <Input
            label="Название шаблона"
            required
            autoFocus
            placeholder="Например: Диплом очный"
            maxLength={MAX_NAME_LENGTH}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          {/* The kind is fixed at creation: it decides which nomination slot the
              template can fill, and what the renderer will and will not draw. */}
          <Select
            label="Тип документа"
            required
            options={DOCUMENT_TYPE_OPTIONS}
            value={type}
            onValueChange={(next) => setType(next as DocumentType)}
            description={documentTypeConfig(type).hint}
          />
          <Textarea
            label="Описание"
            placeholder="Необязательно: короткое пояснение для команды."
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
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

function TemplateCard({ template }: { template: DiplomaTemplate }): React.JSX.Element {
  const updated = formatDate(template.updatedAt);
  const kind = documentTypeConfig(template.type);
  return (
    <Card className="flex flex-col">
      <CardHeader className="space-y-1">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{template.name}</CardTitle>
          {/* The kind is the card's most consequential fact — it decides which
              nomination slot the template can fill. */}
          <Badge variant={kind.tone} size="sm" className="shrink-0">
            {kind.label}
          </Badge>
        </div>
        {template.description ? (
          <p className="line-clamp-2 text-muted-foreground text-sm">{template.description}</p>
        ) : null}
      </CardHeader>
      <CardContent className="mt-auto flex items-center justify-between gap-2 pt-0">
        <div className="text-muted-foreground text-xs">
          <span>Использований: {template.usageCount}</span>
          {updated ? <span className="ml-3">Изменён: {updated}</span> : null}
        </div>
        <Button asChild variant="ghost" size="sm">
          <Link
            to={generatePath(ROUTES.staffDiplomaTemplateConstructor, { templateId: template.id })}
          >
            <PenTool className="size-4" aria-hidden="true" />
            Конструктор
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

export function TemplatesSection(): React.JSX.Element {
  const templatesQuery = useDiplomaTemplates();

  if (templatesQuery.isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {[0, 1, 2, 3].map((key) => (
          <Skeleton key={key} className="h-40 w-full" />
        ))}
      </div>
    );
  }

  if (templatesQuery.isError) {
    const message =
      templatesQuery.error instanceof ApiError
        ? (templatesQuery.error.problem?.detail ?? "Не удалось загрузить шаблоны.")
        : "Не удалось загрузить шаблоны.";
    return (
      <EmptyState
        title="Не удалось загрузить шаблоны"
        description={message}
        action={<Button onClick={() => void templatesQuery.refetch()}>Повторить</Button>}
      />
    );
  }

  const templates = templatesQuery.data ?? [];
  if (templates.length === 0) {
    return (
      <EmptyState
        icon={<LayoutTemplate className="size-6" aria-hidden="true" />}
        title="У вас пока нет шаблонов документов"
        description="Создайте первый шаблон — диплома или благодарности — чтобы начать работу с генерацией."
        action={<CreateTemplateDialog />}
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-muted-foreground text-sm">
          Библиотека шаблонов — самостоятельная и полностью в вашем управлении.
        </p>
        <CreateTemplateDialog />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {templates.map((template) => (
          <TemplateCard key={template.id} template={template} />
        ))}
      </div>
    </div>
  );
}
