import { AlignCenter, AlignLeft, AlignRight, Bold, Italic, Underline } from "lucide-react";
import { useMemo } from "react";
import {
  FIELD_TYPES,
  type FontFamily,
  NOMINATION_PARTS,
  type NominationPartKey,
  type TemplateField,
  type TemplateFieldConfig,
  type TemplateFieldStyle,
  type TemplateTextAlign,
  useFontFaces,
} from "@/features/diplomas";
import { Checkbox, IconButton, Input, Select, type SelectOption, Textarea } from "@/shared/ui";
import type { FieldGeometryPatch } from "../model/use-constructor-fields";

/**
 * The font list, built from what the renderer can actually draw.
 *
 * It used to be seven hard-coded names and the backend had files for none of them, so every
 * diploma printed in the fallback face whatever the editor showed. Now the catalog is served:
 * a family reaches this list only once a file for it exists, and an organizer's own uploads
 * appear here without a release.
 *
 * A substituted name says so in its label. "Arial" cannot be shipped by anyone, and an
 * organizer who picks it should learn that it prints as Liberation Sans here rather than at
 * the ceremony.
 */
function fontOptions(families: readonly FontFamily[], chosen: string): SelectOption[] {
  const options: SelectOption[] = families.map((family) => ({
    value: family.family,
    label:
      family.substitutedBy == null ? family.family : `${family.family} → ${family.substitutedBy}`,
  }));
  // A template saved against a family that has since been removed from the library keeps its
  // value visible instead of silently snapping to whatever sorts first.
  if (chosen && !options.some((option) => option.value === chosen)) {
    options.unshift({ value: chosen, label: `${chosen} (нет в библиотеке)` });
  }
  return options;
}

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
  onValueChange: (value: string) => void;
  onConfigChange: (patch: Partial<TemplateFieldConfig>) => void;
}

/**
 * The data-source section for the nomination block: an editable prefix and a
 * checkbox per part. Toggling a part preserves the canonical order (it never
 * reorders); the preview updates instantly.
 */
function NominationBlockSection({
  config,
  onConfigChange,
}: {
  config: TemplateFieldConfig;
  onConfigChange: (patch: Partial<TemplateFieldConfig>) => void;
}): React.JSX.Element {
  const selected = new Set(config.parts ?? []);
  const toggle = (key: NominationPartKey, on: boolean): void => {
    const next = NOMINATION_PARTS.map((part) => part.key).filter((key2) =>
      key2 === key ? on : selected.has(key2),
    );
    onConfigChange({ parts: next });
  };

  return (
    <Section>
      <SectionTitle>Источник данных</SectionTitle>
      <Input
        aria-label="Префикс"
        placeholder="Префикс, напр. «Жанр:»"
        value={config.prefix ?? ""}
        onChange={(event) => onConfigChange({ prefix: event.target.value })}
      />
      <p className="mt-1 text-muted-foreground text-xs">Части блока</p>
      <div className="flex flex-col gap-2">
        {NOMINATION_PARTS.map((part) => (
          <Checkbox
            key={part.key}
            label={part.label}
            checked={selected.has(part.key)}
            onCheckedChange={(checked) => toggle(part.key, checked === true)}
          />
        ))}
      </div>
    </Section>
  );
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
  onValueChange,
  onConfigChange,
}: FieldInspectorProps): React.JSX.Element {
  const { style } = field;
  const pct = (value: number): number => Math.round(value * 1000) / 10;
  // Also loads the `@font-face` rules, so the canvas beside this panel draws with the same
  // files the PDF will embed rather than with a system fallback.
  const families: FontFamily[] = useFontFaces();
  const fontChoices = useMemo(
    () => fontOptions(families, style.fontFamily),
    [families, style.fontFamily],
  );

  return (
    <div className="scrollbar-custom flex min-h-0 flex-1 flex-col overflow-y-auto">
      <Section>
        <SectionTitle>Элемент</SectionTitle>
        <p className="font-medium text-foreground text-sm">{typeLabel(field.type)}</p>
      </Section>

      {field.config?.parts ? (
        <NominationBlockSection config={field.config} onConfigChange={onConfigChange} />
      ) : field.binding !== null ? (
        <Section>
          <SectionTitle>Источник данных</SectionTitle>
          {/* Read-only — a data-bound field draws its value at generation. */}
          <p className="text-foreground text-sm">{typeLabel(field.type)}</p>
          <p className="font-mono text-muted-foreground text-xs">{field.binding}</p>
        </Section>
      ) : (
        <Section>
          <SectionTitle>Текст</SectionTitle>
          <Textarea
            aria-label="Текст"
            rows={2}
            value={field.value ?? ""}
            onChange={(event) => onValueChange(event.target.value)}
          />
        </Section>
      )}

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
          options={fontChoices}
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
