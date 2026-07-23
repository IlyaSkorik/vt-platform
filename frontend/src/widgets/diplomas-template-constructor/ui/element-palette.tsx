import { FIELD_TYPES, type TemplateFieldType } from "@/features/diplomas";
import { cn } from "@/shared/lib";
import { useConstructorFieldsContext } from "../model/fields-context";

// Only ParticipantName is placeable in this milestone; the rest are the
// type foundation and stay inert until their renderers land.
const PLACEABLE_TYPES = new Set(["participant_name"]);

interface PaletteItemProps {
  field: TemplateFieldType;
  onAdd?: () => void;
}

/**
 * A palette element. When placeable it's a real button that adds an instance on
 * every click; otherwise a non-interactive chip. Either way the markup is the
 * same, so drag & drop can later attach to any of them without a rewrite.
 */
function PaletteItem({ field, onAdd }: PaletteItemProps): React.JSX.Element {
  const Icon = field.icon;
  const className = cn(
    "flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-left text-sm text-foreground transition-colors",
    onAdd
      ? "cursor-pointer hover:border-primary/50 hover:bg-accent/60"
      : "cursor-grab opacity-90 hover:border-primary/40 hover:bg-accent/50",
  );
  const content = (
    <>
      <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <span className="truncate">{field.label}</span>
    </>
  );

  if (onAdd) {
    return (
      <button type="button" onClick={onAdd} className={cn(className, "w-full")}>
        {content}
      </button>
    );
  }
  return (
    <div className={className} aria-disabled="true" title="Появится на следующем этапе">
      {content}
    </div>
  );
}

export function ElementPalette(): React.JSX.Element {
  const { addField } = useConstructorFieldsContext();

  return (
    <aside
      aria-label="Панель инструментов"
      className="flex w-full shrink-0 flex-col border-border border-b bg-card md:w-64 md:border-r md:border-b-0"
    >
      <div className="border-border border-b px-4 py-3">
        <h2 className="font-medium text-foreground text-sm">Элементы</h2>
        <p className="mt-0.5 text-muted-foreground text-xs">
          Нажмите, чтобы добавить элемент на страницу.
        </p>
      </div>
      <div className="flex flex-col gap-2 overflow-y-auto p-3">
        {FIELD_TYPES.map((field) => (
          <PaletteItem
            key={field.id}
            field={field}
            {...(PLACEABLE_TYPES.has(field.id) ? { onAdd: () => addField(field.id) } : {})}
          />
        ))}
      </div>
    </aside>
  );
}
