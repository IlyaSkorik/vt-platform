import {
  allowsFieldType,
  type DocumentType,
  defaultBindingForType,
  documentTypeConfig,
  FIELD_GROUPS,
  FIELD_TYPES,
  type TemplateFieldType,
} from "@/features/diplomas";
import { cn } from "@/shared/lib";
import { useConstructorFieldsContext } from "../model/fields-context";

/**
 * A palette element is placeable when it resolves to real data — a free-text
 * field, or a data field whose type has a binding in the catalogue. Everything
 * else (e.g. QR, whose renderer has not landed) stays an inert chip. Derived, not
 * hardcoded: adding a field to the catalogue makes it placeable automatically.
 */
function isPlaceable(field: TemplateFieldType): boolean {
  return field.binding === "free" || defaultBindingForType(field.id) !== "";
}

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

interface ElementPaletteProps {
  /** The template's kind — decides which elements it may carry. */
  documentType: DocumentType;
}

export function ElementPalette({ documentType }: ElementPaletteProps): React.JSX.Element {
  const { addField } = useConstructorFieldsContext();
  const kind = documentTypeConfig(documentType);
  // Only what this kind of document can print. The backend rejects the rest on
  // save, so offering them would be a dead end.
  const available = FIELD_TYPES.filter((field) => allowsFieldType(documentType, field.id));

  return (
    <aside
      aria-label="Панель инструментов"
      className="flex w-full shrink-0 flex-col border-border border-b bg-card md:w-64 md:border-r md:border-b-0"
    >
      <div className="border-border border-b px-4 py-3">
        <h2 className="font-medium text-foreground text-sm">Элементы</h2>
        <p className="mt-0.5 text-muted-foreground text-xs">
          {documentType === "DIPLOMA"
            ? "Нажмите, чтобы добавить элемент на страницу."
            : `Набор для документа «${kind.label}»: без степени, номера и QR-кода.`}
        </p>
      </div>
      <div className="scrollbar-custom flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-3">
        {FIELD_GROUPS.map((group) => {
          const items = available.filter((field) => field.group === group);
          if (items.length === 0) {
            return null;
          }
          return (
            <section key={group} className="flex flex-col gap-2">
              <h3 className="px-1 font-medium text-muted-foreground text-xs uppercase tracking-wide">
                {group}
              </h3>
              {items.map((field) => (
                <PaletteItem
                  key={field.id}
                  field={field}
                  {...(isPlaceable(field) ? { onAdd: () => addField(field.id) } : {})}
                />
              ))}
            </section>
          );
        })}
      </div>
    </aside>
  );
}
