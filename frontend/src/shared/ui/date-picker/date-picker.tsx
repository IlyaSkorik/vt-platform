import { CalendarDays, X } from "lucide-react";
import { useId, useState } from "react";

import { cn } from "@/shared/lib/cn";
import { Calendar } from "../calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../popover";
import { TimePicker } from "../time-picker";
import {
  formatDateLabel,
  formatDateValue,
  joinDateTime,
  parseDateValue,
  splitDateTime,
} from "./lib";
import type { DatePickerProps, DateTimePickerProps } from "./types";

/**
 * DatePicker — a date field that opens a calendar instead of the browser's own.
 *
 * It replaces `<input type="date">`, whose entire appearance and behaviour is the
 * browser's: Chrome, Firefox and Safari each draw a different control, none of
 * them themeable, and on desktop Firefox the calendar is barely usable. The value
 * on the wire is unchanged (`YYYY-MM-DD`), so this is a change of control rather
 * than of contract — which is what let every form keep its payload mapping.
 *
 * The trigger is a button, not a text field: a half-typed date is a state with no
 * good answer, and the year dropdown in the calendar covers the case typing was
 * for (a birth date eleven years back is two clicks).
 */
export function DatePicker({
  id,
  value,
  onChange,
  label,
  description,
  error,
  required,
  disabled,
  placeholder = "Выберите дату",
  disabledDates,
  fromYear,
  toYear,
  clearable = true,
  containerClassName,
  className,
}: DatePickerProps): React.JSX.Element {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const descriptionId = `${fieldId}-description`;
  const messageId = `${fieldId}-message`;
  const labelId = `${fieldId}-label`;
  const valueId = `${fieldId}-value`;
  const [open, setOpen] = useState(false);

  const selected = parseDateValue(value);
  const shown = formatDateLabel(value);
  const hasError = error != null && error !== false;

  const describedBy =
    [description != null ? descriptionId : null, hasError ? messageId : null]
      .filter(Boolean)
      .join(" ") || undefined;

  return (
    <div className={cn("flex flex-col gap-1.5", containerClassName)}>
      {label != null && (
        <label id={labelId} htmlFor={fieldId} className="font-medium text-foreground text-sm">
          {label}
          {required && (
            <span className="ml-0.5 text-danger" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}

      <div className="relative">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger
            id={fieldId}
            type="button"
            disabled={disabled}
            aria-invalid={hasError || undefined}
            // Both the field's name and its current value, in that order. A
            // `<label htmlFor>` alone would make the accessible name "Дата
            // рождения" and stop there — the button's own text is overridden by
            // the label, so the chosen date would be visible and unannounced.
            {...(label != null ? { "aria-labelledby": `${labelId} ${valueId}` } : {})}
            {...(describedBy != null ? { "aria-describedby": describedBy } : {})}
            className={cn(
              "flex h-9 w-full cursor-pointer items-center gap-2 rounded-md border border-input bg-background px-3 text-left text-foreground text-sm shadow-elevation-1 outline-none transition-colors",
              "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50",
              "disabled:cursor-not-allowed disabled:opacity-50",
              hasError && "border-danger focus-visible:border-danger focus-visible:ring-danger/40",
              // Room for the clear button, so a long date does not run under it.
              clearable && shown != null && !disabled && "pr-9",
              className,
            )}
          >
            <CalendarDays className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <span id={valueId} className={cn("truncate", shown == null && "text-muted-foreground")}>
              {shown ?? placeholder}
            </span>
          </PopoverTrigger>
          <PopoverContent>
            <Calendar
              autoFocus
              {...(selected !== undefined ? { selected } : {})}
              {...(disabledDates !== undefined ? { disabled: disabledDates } : {})}
              {...(fromYear !== undefined ? { fromYear } : {})}
              {...(toYear !== undefined ? { toYear } : {})}
              onSelect={(date) => {
                // `undefined` means the same day was clicked again. Treated as
                // "no change" rather than "clear": the X button is how a date is
                // removed, and losing one to a stray second click is a bad trade.
                if (date != null) {
                  onChange(formatDateValue(date));
                  setOpen(false);
                }
              }}
            />
          </PopoverContent>
        </Popover>

        {clearable && shown != null && !disabled ? (
          <button
            type="button"
            aria-label="Очистить дату"
            onClick={() => onChange("")}
            className="-translate-y-1/2 absolute top-1/2 right-2 inline-flex size-5 cursor-pointer items-center justify-center rounded-sm text-muted-foreground outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            <X className="size-3.5" aria-hidden="true" />
          </button>
        ) : null}
      </div>

      {description != null && !hasError && (
        <p id={descriptionId} className="text-muted-foreground text-xs">
          {description}
        </p>
      )}
      {hasError && (
        <p id={messageId} className="text-danger text-xs">
          {error}
        </p>
      )}
    </div>
  );
}

/**
 * DateTimePicker — the same calendar, with the hour beside it.
 *
 * Two controls rather than one, because they are answered differently: the day is
 * pointed at, the time is typed. A dropdown of quarter-hour slots was the
 * alternative and was rejected — a festival's running order puts numbers on at
 * 11:47, and a list of round times would be in the way at every one of them.
 *
 * The value stays `YYYY-MM-DDTHH:mm`, what `<input type="datetime-local">` gave.
 */
export function DateTimePicker({
  value,
  onChange,
  label,
  timeLabel = "Время",
  description,
  error,
  required,
  disabled,
  requireTime = false,
  containerClassName,
  ...rest
}: DateTimePickerProps): React.JSX.Element {
  const { date, time } = splitDateTime(value);
  // With `requireTime` a day carries no invented hour, so the value keeps the day and
  // an empty time (`2026-05-20T`) until one is given. Whoever reads it sees something
  // that is not an instant, which is the truth.
  const join = (nextDate: string, nextTime: string) =>
    requireTime
      ? nextDate === ""
        ? ""
        : `${nextDate}T${nextTime}`
      : joinDateTime(nextDate, nextTime);

  return (
    <div className={cn("flex flex-col gap-1.5", containerClassName)}>
      <div className="flex items-end gap-2">
        <DatePicker
          {...rest}
          containerClassName="flex-1 min-w-0"
          value={date}
          onChange={(next) => onChange(join(next, time))}
          {...(label != null ? { label } : {})}
          {...(required != null ? { required } : {})}
          {...(disabled != null ? { disabled } : {})}
          {...(error != null ? { error: "" } : {})}
        />
        <TimePicker
          containerClassName="w-32 shrink-0"
          label={timeLabel}
          value={time}
          // A time with no day names no instant, so the field stays inert until
          // there is one — rather than accepting input that cannot be saved.
          disabled={disabled === true || date === ""}
          onChange={(next) => {
            // Rubbing the time out to retype it is not "this day starts at
            // midnight". Where a day alone is an answer there is nothing to
            // report yet, so the value keeps its last real time and the day's
            // own ✕ clears the lot; where it is not, an empty hour is a state
            // the value can hold, and says the instant is not settled.
            if (next === "" && !requireTime) {
              return;
            }
            onChange(join(date, next));
          }}
        />
      </div>
      {description != null && error == null && (
        <p className="text-muted-foreground text-xs">{description}</p>
      )}
      {error != null && error !== false && <p className="text-danger text-xs">{error}</p>}
    </div>
  );
}
