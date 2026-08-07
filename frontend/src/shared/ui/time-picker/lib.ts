/**
 * Turning half-typed keystrokes into a time.
 *
 * The field is typed into far more often than it is clicked, so the interesting
 * states are all the incomplete ones — `1`, `11`, `114` — and none of them is a
 * time yet. These functions keep "what is on screen" and "what is worth
 * reporting" apart, which is what lets someone type through `9` on the way to
 * `9:45` without the form deciding they meant nine o'clock.
 */

/** Digits only, at most four: `9:4x5` → `945`. */
export function digitsOf(value: string): string {
  return value.replace(/\D/g, "").slice(0, 4);
}

/**
 * Lay a colon into whatever has been typed so far.
 *
 * A single leading digit above 2 can only start a one-digit hour (`9` → `09:`),
 * so the colon lands early and the next keystroke is already a minute. Typing
 * `0945` and typing `945` both arrive at `09:45`.
 */
export function maskTime(value: string): string {
  const digits = digitsOf(value);
  if (digits.length === 0) {
    return "";
  }
  if (digits.length === 1) {
    return Number(digits) > 2 ? `0${digits}:` : digits;
  }
  if (digits.length === 2) {
    return Number(digits) > 23 ? `0${digits[0]}:${digits[1]}` : digits;
  }
  // Three digits led by one that cannot start an hour is `h:mm` — the shape a
  // pasted "945" has. Typing reaches the same place a keystroke earlier, since
  // the colon was already laid in at "9".
  if (digits.length === 3 && Number(digits[0]) > 2) {
    return `0${digits[0]}:${digits.slice(1)}`;
  }
  return `${digits.slice(0, 2)}:${digits.slice(2)}`;
}

/** `9:5` → `09:05`; anything that is not a time on a clock → `""`. */
export function normaliseTime(value: string): string {
  const match = /^(\d{1,2}):(\d{1,2})$/.exec(value.trim());
  if (match == null) {
    return "";
  }
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) {
    return "";
  }
  return `${pad(hours)}:${pad(minutes)}`;
}

/**
 * Step one part of a time up or down, wrapping at both ends.
 *
 * Wrapping rather than clamping: 23:00 + 1 hour is midnight everywhere except in
 * software that stopped counting. An empty field starts from midnight, so the
 * first press of Up gives a usable value rather than nothing.
 */
export function stepTime(value: string, part: "hours" | "minutes", delta: number): string {
  const current = normaliseTime(value);
  const [hours, minutes] = current === "" ? [0, 0] : current.split(":").map(Number);
  if (part === "hours") {
    return `${pad(wrap((hours ?? 0) + delta, 24))}:${pad(minutes ?? 0)}`;
  }
  return `${pad(hours ?? 0)}:${pad(wrap((minutes ?? 0) + delta, 60))}`;
}

/** Which half of `HH:MM` the caret is sitting in. */
export function partAtCaret(caret: number | null): "hours" | "minutes" {
  return caret != null && caret > 2 ? "minutes" : "hours";
}

function wrap(value: number, size: number): number {
  return ((value % size) + size) % size;
}

function pad(value: number): string {
  return String(value).padStart(2, "0");
}
