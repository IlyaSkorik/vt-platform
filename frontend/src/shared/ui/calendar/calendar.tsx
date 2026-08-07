import { ChevronLeft, ChevronRight } from "lucide-react";
import { DayPicker, type DropdownProps, getDefaultClassNames } from "react-day-picker";
import { ru } from "react-day-picker/locale";

import { cn } from "@/shared/lib/cn";
import { Select } from "../select";
import type { CalendarProps } from "./types";

/**
 * The month and year dropdowns, as our own `Select` rather than a native one.
 *
 * The library renders `<select>`, and a native dropdown's popup is drawn by the
 * browser: it takes no token, ignores the theme, and on dark themes came out as
 * white text on a white list. Swapping the component is also the only way — the
 * popup is not part of the page and no stylesheet reaches it.
 *
 * `onChange` is handed a change event because that is what the library expects
 * from a `<select>`; it reads `target.value` and nothing else, so the shape is
 * enough. Narrower than a cast on the whole component, and it fails loudly if
 * that ever stops being true.
 */
function CaptionDropdown({ options, value, onChange, "aria-label": ariaLabel }: DropdownProps) {
  return (
    <Select
      size="sm"
      className="w-auto gap-1 border-none px-2 font-medium shadow-none hover:bg-accent"
      {...(value != null ? { value: String(value) } : {})}
      {...(ariaLabel != null ? { "aria-label": ariaLabel } : {})}
      onValueChange={(next) =>
        onChange?.({ target: { value: next } } as React.ChangeEvent<HTMLSelectElement>)
      }
      options={(options ?? []).map((option) => ({
        value: String(option.value),
        label: option.label,
        disabled: option.disabled,
      }))}
    />
  );
}

/**
 * Calendar — the month grid, styled onto the platform's tokens.
 *
 * `react-day-picker` supplies the behaviour that is genuinely hard to get right
 * and easy to get wrong invisibly: roving focus across the grid, arrow/Home/End/
 * PageUp navigation, `role="grid"` semantics and the labels a screen reader reads
 * out. Everything visible here is ours — the library ships no styles we use.
 *
 * Month and year are dropdowns rather than a pair of arrows, because the field
 * this most often fills is a child's date of birth: eleven years back is two
 * clicks this way and a hundred and thirty otherwise.
 */
export function Calendar({
  selected,
  onSelect,
  defaultMonth,
  disabled,
  autoFocus,
  fromYear,
  toYear,
  className,
}: CalendarProps): React.JSX.Element {
  const defaults = getDefaultClassNames();
  const now = new Date();
  // A window wide enough for both ends of the platform's real range: a
  // grandparent's birth date at one end, a festival two years out at the other.
  const startMonth = new Date(fromYear ?? now.getFullYear() - 100, 0);
  const endMonth = new Date(toYear ?? now.getFullYear() + 5, 11);
  const openOn = selected ?? defaultMonth;

  return (
    <DayPicker
      mode="single"
      locale={ru}
      // Monday. `ru` already says so; stated because a calendar that silently
      // starts on Sunday is the kind of thing nobody reports and everybody misreads.
      weekStartsOn={1}
      showOutsideDays
      captionLayout="dropdown"
      startMonth={startMonth}
      endMonth={endMonth}
      // Spread conditionally rather than passed as `undefined`: the library
      // declares these as optional-and-not-undefined, which `exactOptionalPropertyTypes`
      // takes at its word.
      //
      // The month a picker opens on is the chosen day if there is one, else the
      // caller's hint, else today — opening on today when a 2014 birth date is
      // already set would hide the answer the user came back to change.
      {...(openOn !== undefined ? { defaultMonth: openOn } : {})}
      {...(selected !== undefined ? { selected } : {})}
      {...(onSelect !== undefined ? { onSelect } : {})}
      {...(disabled !== undefined ? { disabled } : {})}
      {...(autoFocus !== undefined ? { autoFocus } : {})}
      className={cn("w-fit", className)}
      classNames={{
        ...defaults,
        root: cn(defaults.root, "text-foreground"),
        months: "flex flex-col gap-3",
        month: "flex flex-col gap-3",
        month_caption: "flex items-center justify-center px-9",
        dropdowns: "flex items-center gap-1.5",
        dropdown_root: "",
        dropdown: "",
        // The library still renders a caption label beside the dropdowns, saying
        // the same thing twice. Hidden rather than removed: it is what a screen
        // reader announces the grid by.
        caption_label: "sr-only",
        nav: "absolute inset-x-0 top-0 flex items-center justify-between",
        button_previous:
          "inline-flex size-8 items-center justify-center rounded-md text-muted-foreground outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-40",
        button_next:
          "inline-flex size-8 items-center justify-center rounded-md text-muted-foreground outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-40",
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday: "w-9 pb-1 font-normal text-[0.75rem] text-muted-foreground capitalize",
        week: "flex w-full",
        day: "p-0.5",
        day_button:
          "inline-flex size-8 cursor-pointer items-center justify-center rounded-md text-sm tabular-nums outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50",
        selected:
          "[&>button]:bg-primary [&>button]:text-primary-foreground [&>button]:hover:bg-primary [&>button]:hover:text-primary-foreground",
        // Today is an outline rather than a fill, so it cannot be mistaken for
        // the selection when both are on screen.
        today: "[&>button]:ring-1 [&>button]:ring-primary/50",
        outside: "[&>button]:text-muted-foreground/50",
        disabled: "[&>button]:pointer-events-none [&>button]:opacity-40",
        hidden: "invisible",
      }}
      components={{
        Dropdown: CaptionDropdown,
        Chevron: ({ orientation, ...rest }) =>
          orientation === "left" ? (
            <ChevronLeft className="size-4" aria-hidden="true" {...rest} />
          ) : (
            <ChevronRight className="size-4" aria-hidden="true" {...rest} />
          ),
      }}
    />
  );
}
