import { SlidersHorizontal } from "lucide-react";

/** Properties that will become editable once a field is selected on the canvas. */
const FUTURE_PROPERTIES = [
  "Координаты",
  "Размеры",
  "Шрифт",
  "Цвет",
  "Выравнивание",
  "Перенос",
  "Автоуменьшение",
  "Привязка данных",
];

export function PropertiesPanel(): React.JSX.Element {
  return (
    <aside
      aria-label="Свойства"
      className="flex w-full shrink-0 flex-col border-border border-t bg-card md:w-72 md:border-t-0 md:border-l"
    >
      <div className="border-border border-b px-4 py-3">
        <h2 className="font-medium text-foreground text-sm">Свойства</h2>
      </div>
      <div className="flex flex-1 flex-col gap-4 p-4">
        <div className="flex flex-col items-center gap-2 rounded-md border border-border border-dashed bg-muted/30 px-4 py-6 text-center">
          <span className="flex size-9 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <SlidersHorizontal className="size-4" aria-hidden="true" />
          </span>
          <p className="text-muted-foreground text-sm">
            Выберите поле, чтобы настроить его свойства.
          </p>
        </div>
        <div>
          <p className="mb-2 text-muted-foreground text-xs uppercase tracking-wide">
            Позже здесь появятся
          </p>
          <ul className="flex flex-col gap-1 text-muted-foreground text-sm">
            {FUTURE_PROPERTIES.map((property) => (
              <li key={property} className="flex items-center gap-2">
                <span className="size-1.5 rounded-full bg-border" aria-hidden="true" />
                {property}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  );
}
