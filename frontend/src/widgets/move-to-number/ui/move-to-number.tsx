import { ArrowUpDown } from "lucide-react";
import { useState } from "react";

import { Button, Divider, Input, Popover, PopoverContent, PopoverTrigger } from "@/shared/ui";

/** Where a moved slot lands relative to the number it was pointed at. */
export type MovePlacement = "before" | "after";

export interface MoveToNumberProps {
  /** What is being moved, used for the control's accessible name. */
  label: string;
  /**
   * The number that slot carries now, so the form says what it is about — `null` for a
   * slot that has none (перерыв, награждение), which is then named by its title instead.
   */
  current: number | null;
  /** Whether the slot is already first / last, which is what greys out the shortcuts. */
  atStart: boolean;
  atEnd: boolean;
  disabled?: boolean;
  /**
   * Place the slot next to `number`. Returning `false` keeps the form open — the caller
   * has already said what was wrong (usually: no such number), and a typo is quicker to
   * correct than the whole move is to reopen.
   */
  onPlace: (number: number, placement: MovePlacement) => boolean;
  onMoveToStart: () => void;
  onMoveToEnd: () => void;
}

/**
 * "Перенести" — the move the arrows cannot make.
 *
 * A step at a time is right for a correction and hopeless while the day is running: the
 * act being announced next is at the bottom of a forty-row programme and belongs at the
 * top *now*. So the target is named rather than walked to — by the number printed in the
 * programme everyone in the hall is holding, which after a freeze is not the row's index.
 *
 * Two buttons instead of a mode switch, because "перед" and "после" are the whole
 * vocabulary of the move and choosing costs a click either way; "в начало" and "в конец"
 * are one click because they are what this is opened for most often.
 */
export function MoveToNumber({
  label,
  current,
  atStart,
  atEnd,
  disabled = false,
  onPlace,
  onMoveToStart,
  onMoveToEnd,
}: MoveToNumberProps): React.JSX.Element {
  const [open, setOpen] = useState(false);
  const [target, setTarget] = useState("");
  const number = Number.parseInt(target, 10);
  const named = Number.isFinite(number) && number > 0;

  const close = () => {
    setTarget("");
    setOpen(false);
  };

  const place = (placement: MovePlacement) => {
    if (named && onPlace(number, placement)) {
      close();
    }
  };

  const jump = (move: () => void) => {
    move();
    close();
  };

  return (
    <Popover open={open} onOpenChange={(next) => (next ? setOpen(true) : close())}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="xs"
          aria-label={`Перенести: ${label}`}
          disabled={disabled || (atStart && atEnd)}
        >
          <ArrowUpDown className="size-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72">
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            place("after");
          }}
        >
          <p className="font-medium text-sm">
            {current === null ? `Перенести «${label}»` : `Перенести №${current}`}
          </p>
          <Input
            label="Рядом с номером"
            description="Enter — поставить после него."
            type="number"
            min={1}
            inputMode="numeric"
            value={target}
            onChange={(event) => setTarget(event.target.value)}
          />
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="flex-1"
              disabled={!named || disabled}
              onClick={() => place("before")}
            >
              Перед
            </Button>
            <Button type="submit" size="sm" className="flex-1" disabled={!named || disabled}>
              После
            </Button>
          </div>
          <Divider />
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="flex-1"
              disabled={atStart || disabled}
              onClick={() => jump(onMoveToStart)}
            >
              В начало
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="flex-1"
              disabled={atEnd || disabled}
              onClick={() => jump(onMoveToEnd)}
            >
              В конец
            </Button>
          </div>
        </form>
      </PopoverContent>
    </Popover>
  );
}
