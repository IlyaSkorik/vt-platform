import { AlignCenter, AlignLeft, AlignRight, Bold, Italic, Underline } from "lucide-react";
import {
  FIELD_TYPES,
  type TemplateField,
  type TemplateFieldStyle,
  type TemplateTextAlign,
} from "@/features/diplomas";
import { Checkbox, IconButton, Input, Select, type SelectOption } from "@/shared/ui";
import type { FieldGeometryPatch } from "../model/use-constructor-fields";

const FONT_OPTIONS: SelectOption[] = [
  { value: "Montserrat", label: "Montserrat" },
  { value: "Arial", label: "Arial" },
  { value: "Times New Roman", label: "Times New Roman" },
  { value: "Georgia", label: "Georgia" },
  { value: "Roboto", label: "Roboto" },
  { value: "Open Sans", label: "Open Sans" },
  { value: "PT Sans", label: "PT Sans" },
];

const ALIGNMENTS: ReadonlyArray<{
  value: TemplateTextAlign;
  icon: typeof AlignLeft;
  label: string;
}> = [
  { value: "left", icon: AlignLeft, label: "Слева" },
  { value: "center", icon: AlignCenter, label: "По центру" },
  { value: "right", icon: AlignRight, label: "Справа" },
];

function typeLabel(type: string): string {
  return FIELD_TYPES.find((field) => field.id === type)?.label ?? type;
}

function Section({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <div className="flex flex-col gap-3 border-border border-b p-4">{children}</div>;
}

function SectionTitle({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">{children}</p>
  );
}

/** A compact numeric input with a caption, for the geometry/size grid. */
function NumberField({
  label,
  value,
  onCommit,
  min,
  max,
  step = 1,
  suffix,
}: {
  label: string;
  value: number;
  onCommit: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
}): React.JSX.Element {
  return (
    <div className="flex flex-col gap-1 text-muted-foreground text-xs">
      <span>{label}</span>
      <div className="relative">
        <Input
          type="number"
          aria-label={label}
          value={String(value)}
          min={min}
          max={max}
          step={step}
          onChange={(event) => {
            const next = Number(event.target.value);
            if (!Number.isNaN(next)) {
              onCommit(next);
            }
          }}
          className={suffix ? "pr-7" : undefined}
        />
        {suffix ? (
          <span className="-translate-y-1/2 absolute top-1/2 right-2 text-muted-foreground text-xs">
            {suffix}
          </span>
        ) : null}
      </div>
    </div>
  );
}

interface FieldInspectorProps {
  field: TemplateField;
  onGeometryChange: (patch: FieldGeometryPatch) => void;
  onStyleChange: (patch: Partial<TemplateFieldStyle>) => void;
}

/**
 * The properties inspector for the selected field — a Figma-style panel. Every
 * change is applied to the model immediately (instant preview); nothing is saved
 * to the server here. Only appearance/geometry is edited, never the field's data.
 */
export function FieldInspector({
  field,
  onGeometryChange,
  onStyleChange,
}: FieldInspectorProps): React.JSX.Element {
  const { style } = field;
  const pct = (value: number): number => Math.round(value * 1000) / 10;

  return (
    <div className="flex flex-col overflow-y-auto">
      <Section>
        <SectionTitle>Элемент</SectionTitle>
        <p className="font-medium text-foreground text-sm">{typeLabel(field.type)}</p>
      </Section>

      <Section>
        <SectionTitle>Позиция и размер</SectionTitle>
        <div className="grid grid-cols-2 gap-3">
          <NumberField
            label="Страница"
            value={field.page}
            min={1}
            onCommit={(value) => onGeometryChange({ page: value })}
          />
          <div />
          <NumberField
            label="X"
            value={pct(field.x)}
            min={0}
            max={100}
            step={0.1}
            suffix="%"
            onCommit={(value) => onGeometryChange({ x: value / 100 })}
          />
          <NumberField
            label="Y"
            value={pct(field.y)}
            min={0}
            max={100}
            step={0.1}
            suffix="%"
            onCommit={(value) => onGeometryChange({ y: value / 100 })}
          />
          <NumberField
            label="Ширина"
            value={pct(field.width)}
            min={0}
            max={100}
            step={0.1}
            suffix="%"
            onCommit={(value) => onGeometryChange({ width: value / 100 })}
          />
          <NumberField
            label="Высота"
            value={pct(field.height)}
            min={0}
            max={100}
            step={0.1}
            suffix="%"
            onCommit={(value) => onGeometryChange({ height: value / 100 })}
          />
        </div>
      </Section>

      <Section>
        <SectionTitle>Текст</SectionTitle>
        <Select
          label="Шрифт"
          options={FONT_OPTIONS}
          value={style.fontFamily}
          onValueChange={(value) => onStyleChange({ fontFamily: value })}
        />
        <div className="flex items-end gap-2">
          <NumberField
            label="Размер"
            value={style.fontSize}
            min={4}
            max={400}
            suffix="pt"
            onCommit={(value) => onStyleChange({ fontSize: value })}
          />
          <div className="flex gap-1">
            <IconButton
              icon={<Bold className="size-4" />}
              aria-label="Жирный"
              aria-pressed={style.fontWeight === "bold"}
              size="sm"
              variant={style.fontWeight === "bold" ? "primary" : "outline"}
              onClick={() =>
                onStyleChange({ fontWeight: style.fontWeight === "bold" ? "normal" : "bold" })
              }
            />
            <IconButton
              icon={<Italic className="size-4" />}
              aria-label="Курсив"
              aria-pressed={style.fontStyle === "italic"}
              size="sm"
              variant={style.fontStyle === "italic" ? "primary" : "outline"}
              onClick={() =>
                onStyleChange({ fontStyle: style.fontStyle === "italic" ? "normal" : "italic" })
              }
            />
            <IconButton
              icon={<Underline className="size-4" />}
              aria-label="Подчёркивание"
              aria-pressed={style.underline}
              size="sm"
              variant={style.underline ? "primary" : "outline"}
              onClick={() => onStyleChange({ underline: !style.underline })}
            />
          </div>
        </div>
      </Section>

      <Section>
        <SectionTitle>Цвет</SectionTitle>
        <div className="flex items-center gap-2">
          <input
            type="color"
            aria-label="Цвет текста"
            value={style.color}
            onChange={(event) => onStyleChange({ color: event.target.value })}
            className="size-9 shrink-0 cursor-pointer rounded-md border border-border bg-background p-0.5"
          />
          <Input
            value={style.color}
            onChange={(event) => onStyleChange({ color: event.target.value })}
            className="font-mono uppercase"
          />
        </div>
      </Section>

      <Section>
        <SectionTitle>Выравнивание</SectionTitle>
        <div className="flex gap-1">
          {ALIGNMENTS.map((alignment) => {
            const Icon = alignment.icon;
            const active = style.textAlign === alignment.value;
            return (
              <IconButton
                key={alignment.value}
                icon={<Icon className="size-4" />}
                aria-label={alignment.label}
                aria-pressed={active}
                size="sm"
                variant={active ? "primary" : "outline"}
                onClick={() => onStyleChange({ textAlign: alignment.value })}
              />
            );
          })}
        </div>
      </Section>

      <Section>
        <Checkbox
          label="Автоуменьшение текста"
          checked={style.autoShrink}
          onCheckedChange={(checked) => onStyleChange({ autoShrink: checked === true })}
        />
        <Checkbox
          label="Перенос строк"
          checked={style.wrapText}
          onCheckedChange={(checked) => onStyleChange({ wrapText: checked === true })}
        />
      </Section>
    </div>
  );
}
