import { SlidersHorizontal } from "lucide-react";
import { useConstructorFieldsContext } from "../model/fields-context";
import { FieldInspector } from "./field-inspector";

/**
 * The right dock. Shows the field inspector when something is selected, and a
 * quiet placeholder otherwise. It only reads the selection and forwards edits to
 * the data layer — no appearance state lives here.
 */
export function PropertiesPanel(): React.JSX.Element {
  const { selectedField, updateGeometry, updateStyle, updateValue, updateConfig } =
    useConstructorFieldsContext();

  return (
    <aside
      aria-label="Свойства"
      className="flex w-full shrink-0 flex-col border-border border-t bg-card md:w-72 md:border-t-0 md:border-l"
    >
      <div className="border-border border-b px-4 py-3">
        <h2 className="font-medium text-foreground text-sm">Свойства</h2>
      </div>
      {selectedField ? (
        <FieldInspector
          field={selectedField}
          onGeometryChange={(patch) => updateGeometry(selectedField.id, patch)}
          onStyleChange={(patch) => updateStyle(selectedField.id, patch)}
          onValueChange={(value) => updateValue(selectedField.id, value)}
          onConfigChange={(patch) => updateConfig(selectedField.id, patch)}
        />
      ) : (
        <div className="flex flex-1 flex-col gap-4 p-4">
          <div className="flex flex-col items-center gap-2 rounded-md border border-border border-dashed bg-muted/30 px-4 py-6 text-center">
            <span className="flex size-9 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <SlidersHorizontal className="size-4" aria-hidden="true" />
            </span>
            <p className="text-muted-foreground text-sm">
              Выберите поле, чтобы настроить его свойства.
            </p>
          </div>
        </div>
      )}
    </aside>
  );
}
