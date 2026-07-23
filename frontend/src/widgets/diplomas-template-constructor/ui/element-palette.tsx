import { FIELD_TYPES, type TemplateFieldType } from "@/features/diplomas";
import { cn } from "@/shared/lib";

/**
 * A single palette element. Rendered as a self-contained tile so that, when
 * drag & drop lands, only this component gains drag handlers — the layout,
 * markup and styling stay identical.
 */
function PaletteItem({ field }: { field: TemplateFieldType }): React.JSX.Element {
  const Icon = field.icon;
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm",
        // Reads as a draggable chip already; interactivity arrives with drag & drop.
        "cursor-grab select-none text-foreground opacity-90 transition-colors hover:border-primary/40 hover:bg-accent/50",
      )}
      aria-disabled="true"
      title="Перетаскивание на PDF появится позже"
    >
      <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <span className="truncate">{field.label}</span>
    </div>
  );
}

export function ElementPalette(): React.JSX.Element {
  return (
    <aside
      aria-label="Панель инструментов"
      className="flex w-full shrink-0 flex-col border-border border-b bg-card md:w-64 md:border-r md:border-b-0"
    >
      <div className="border-border border-b px-4 py-3">
        <h2 className="font-medium text-foreground text-sm">Элементы</h2>
        <p className="mt-0.5 text-muted-foreground text-xs">
          Позже элементы можно будет перетаскивать на PDF.
        </p>
      </div>
      <div className="flex flex-col gap-2 overflow-y-auto p-3">
        {FIELD_TYPES.map((field) => (
          <PaletteItem key={field.id} field={field} />
        ))}
      </div>
    </aside>
  );
}
