import { Clock } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/shared/lib/cn";
import { Input } from "../input";
import { Popover, PopoverContent, PopoverTrigger } from "../popover";
import { digitsOf, maskTime, normaliseTime, partAtCaret, stepTime } from "./lib";
import type { TimePickerProps } from "./types";

const HOURS = Array.from({ length: 24 }, (_, hour) => hour);

/**
 * TimePicker — a time field with the platform's own list instead of the browser's.
 *
 * It replaces `<input type="time">`, whose spinner and clock popup belong to the
 * browser: drawn outside the page, reachable by no token or stylesheet, and
 * different in every one of them. Same reason the month and year dropdowns had to
 * go, and the same fix — render the list as elements in the document.
 *
 * Typing stays the fast path, because that is how a time is actually answered: a
 * running order puts a number on at 11:47, and nobody scrolls to that. The field
 * lays the colon in as digits arrive, so `1147` and `11:47` are the same four
 * keystrokes, and Up/Down step whichever half the caret is in. The columns are
 * for the other case — an even hour, chosen with a mouse.
 *
 * What is on screen and what gets reported are deliberately not the same thing:
 * `1` and `11` and `114` are all states worth showing and none of them is a time,
 * so `onChange` stays quiet until the digits make one.
 */
export function TimePicker({
  id,
  value,
  onChange,
  label,
  description,
  error,
  required,
  disabled,
  minuteStep = 5,
  containerClassName,
  className,
}: TimePickerProps): React.JSX.Element {
  const [draft, setDraft] = useState(() => normaliseTime(value));
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Follow the value when it changes from outside (a form reset, a loaded
  // record) — but never while the field is being typed into, or the mask would
  // fight the caret.
  useEffect(() => {
    const normalised = normaliseTime(value);
    if (document.activeElement !== inputRef.current) {
      setDraft(value === "" ? "" : normalised);
    }
  }, [value]);

  const minutes = Array.from(
    { length: Math.ceil(60 / minuteStep) },
    (_, index) => index * minuteStep,
  );
  const [selectedHour = "", selectedMinute = ""] = normaliseTime(draft).split(":");

  const commit = (next: string): void => {
    setDraft(next);
    const normalised = normaliseTime(next);
    // An empty field is a deliberate "no time" and is reported; a half-typed one
    // is not an answer yet and is left alone until it becomes one.
    if (normalised !== "" || digitsOf(next) === "") {
      onChange(normalised);
    }
  };

  const pick = (part: "hours" | "minutes", picked: number): void => {
    const base = normaliseTime(draft) === "" ? "00:00" : normaliseTime(draft);
    const [hours = "00", mins = "00"] = base.split(":");
    const next =
      part === "hours"
        ? `${String(picked).padStart(2, "0")}:${mins}`
        : `${hours}:${String(picked).padStart(2, "0")}`;
    setDraft(next);
    onChange(next);
  };

  return (
    <div className={cn("flex flex-col gap-1.5", containerClassName)}>
      <Popover open={open} onOpenChange={setOpen}>
        <div className="relative">
          <Input
            ref={inputRef}
            id={id}
            inputMode="numeric"
            autoComplete="off"
            placeholder="--:--"
            maxLength={5}
            className={cn("tabular-nums", className)}
            value={draft}
            disabled={disabled}
            {...(label != null ? { label } : {})}
            {...(description != null ? { description } : {})}
            {...(error != null ? { error } : {})}
            {...(required != null ? { required } : {})}
            onChange={(event) => commit(maskTime(event.target.value))}
            onKeyDown={(event) => {
              if (event.key !== "ArrowUp" && event.key !== "ArrowDown") {
                return;
              }
              // The browser would move the caret to one end of the field instead.
              event.preventDefault();
              const part = partAtCaret(event.currentTarget.selectionStart);
              const next = stepTime(draft, part, event.key === "ArrowUp" ? 1 : -1);
              setDraft(next);
              onChange(next);
            }}
            onBlur={() => {
              // Whatever is left half-typed resolves now: into a time if it can
              // be one, and back to the stored one if it cannot — leaving `11:`
              // on screen would look saved, and leaving the field blank when the
              // consumer still holds 10:00 would look cleared.
              setDraft(normaliseTime(draft) || normaliseTime(value));
            }}
            suffix={
              <PopoverTrigger
                type="button"
                disabled={disabled}
                aria-label="Выбрать время"
                className="-mr-1 inline-flex size-6 cursor-pointer items-center justify-center rounded-sm text-muted-foreground outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed"
              >
                <Clock className="size-4" aria-hidden="true" />
              </PopoverTrigger>
            }
          />
        </div>

        <PopoverContent className="p-0" align="end">
          <div className="flex h-56">
            <Column
              label="Часы"
              values={HOURS}
              selected={selectedHour}
              onPick={(picked) => pick("hours", picked)}
            />
            <div className="w-px bg-border" />
            <Column
              label="Минуты"
              values={minutes}
              selected={selectedMinute}
              onPick={(picked) => pick("minutes", picked)}
            />
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}

/** One scrollable column of the picker; hours or minutes. */
function Column({
  label,
  values,
  selected,
  onPick,
}: {
  label: string;
  values: number[];
  selected: string;
  onPick: (value: number) => void;
}): React.JSX.Element {
  return (
    // A real `<fieldset>`/`<legend>`, not a div with `role="group"`: the column is
    // a set of related choices, which is what the element already means — and the
    // legend names it without a second copy of the label in an aria attribute.
    <fieldset className="flex min-w-0 flex-col border-0 p-0">
      <legend className="px-3 pt-2 pb-1 text-muted-foreground text-xs">{label}</legend>
      {/* The base layer already gives every scrollbar the platform's own look, so
          this is not about replacing a default one — it is about size. A 0.5rem
          bar crowds a column fourteen characters wide; `scrollbar-slim` is the
          same design at a quarter. Stated on the element rather than inherited,
          because this list is rendered through a portal. */}
      <div className="scrollbar-slim min-h-0 flex-1 overflow-y-auto px-1 pb-1">
        {values.map((entry) => {
          const text = String(entry).padStart(2, "0");
          const isSelected = text === selected;
          return (
            <button
              key={entry}
              type="button"
              aria-pressed={isSelected}
              // Scrolled to on open, so a value set an hour down the list is
              // visible rather than something the user has to go looking for.
              ref={
                isSelected
                  ? (node) => {
                      // Optional call, not optional chaining for show: jsdom has
                      // no layout and therefore no `scrollIntoView`, and a test
                      // should not fall over on a scroll position.
                      node?.scrollIntoView?.({ block: "center" });
                    }
                  : undefined
              }
              onClick={() => onPick(entry)}
              className={cn(
                "block w-14 cursor-pointer rounded-sm px-3 py-1.5 text-center text-sm tabular-nums outline-none transition-colors",
                "hover:bg-accent hover:text-accent-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50",
                isSelected &&
                  "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground",
              )}
            >
              {text}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
