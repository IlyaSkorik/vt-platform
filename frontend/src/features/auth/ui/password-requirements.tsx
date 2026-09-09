import { Check, Circle, X } from "lucide-react";
import type { FieldError } from "react-hook-form";
import { cn } from "@/shared/lib/cn";
import { PASSWORD_RULES } from "../model/schemas";

interface PasswordRequirementsProps {
  /** The password as typed; every rule is re-checked on each keystroke. */
  value: string;
  /**
   * Id for the list, so the password field can point at it with
   * `aria-describedby` — the requirements are then read out with the field
   * rather than sitting unannounced beside it.
   */
  id?: string;
  /**
   * Once the field has been rejected, the rules still unmet are the reason.
   * Until then they are simply not done yet, and colouring them as errors would
   * mean greeting an empty field with five red lines.
   */
  invalid?: boolean;
  className?: string;
}

/** The wording {@link PASSWORD_RULES} produces, which the checklist already shows. */
const RULE_MESSAGES: ReadonlySet<string> = new Set(PASSWORD_RULES.map((rule) => rule.message));

/**
 * The message a password field should show, given its error and a
 * {@link PasswordRequirements} list beneath it.
 *
 * A policy failure is already spelled out line by line in the checklist, so
 * repeating one of those lines as the field error states it twice and leaves the
 * other unmet rules unmentioned. The field keeps its invalid styling and points
 * down at the list instead.
 *
 * Anything else is shown verbatim, because it is something the list cannot say:
 * a breached password the server refused, an over-long one, a new password equal
 * to the current one. Which is why the test is the message's *wording* and not
 * the error's `type` — a form may add its own rules to this field, and those
 * still have to reach the reader.
 */
export function passwordFieldError(error: FieldError | undefined): string | undefined {
  if (error == null) {
    return undefined;
  }
  if (error.message == null || RULE_MESSAGES.has(error.message)) {
    return "Пароль не соответствует требованиям ниже";
  }
  return error.message;
}

/**
 * A live checklist of the password policy.
 *
 * "Минимум 12 символов, специальный символ, буквы разного регистра и цифра" as a
 * single sentence asks the reader to hold five rules in their head and audit
 * their own typing against them; when it still fails, one error line names one
 * of the five. So each rule gets its own line and ticks itself off as it is
 * satisfied, which turns choosing a password into following a list.
 *
 * The rules and their predicates come from {@link PASSWORD_RULES}, the same
 * source the validator is built from, so a ticked list means an accepted
 * password (the server may still refuse a breached one — that arrives as a
 * field error).
 *
 * State is carried three ways, never by colour alone (WCAG 2.1 AA §1.4.1): the
 * icon, the colour, and a visually hidden word screen readers announce. The
 * list is a polite live region, so ticking a rule off is spoken as it happens
 * instead of only when the field is re-read.
 */
export function PasswordRequirements({
  value,
  id,
  invalid = false,
  className,
}: PasswordRequirementsProps): React.JSX.Element {
  return (
    <div id={id} className={cn("flex flex-col gap-1", className)}>
      <p className="text-xs text-muted-foreground">Пароль должен содержать:</p>
      {/* biome-ignore lint/a11y/noRedundantRoles: Tailwind's preflight sets `list-style: none`, which drops list semantics in Safari/VoiceOver — the explicit role keeps "5 rules, 2 done" countable */}
      <ul role="list" aria-live="polite" className="flex flex-col gap-1">
        {PASSWORD_RULES.map((rule) => {
          const satisfied = rule.isSatisfied(value);
          const Icon = satisfied ? Check : invalid ? X : Circle;
          return (
            <li
              key={rule.id}
              className={cn(
                "flex items-center gap-1.5 text-xs transition-colors",
                satisfied ? "text-success" : invalid ? "text-danger" : "text-muted-foreground",
              )}
            >
              <Icon className="size-3.5 shrink-0" aria-hidden="true" />
              <span>{rule.label}</span>
              {/* The state in words as well as in icon and colour, and inside the live
                  region, so ticking a rule off is spoken rather than only seen. */}
              <span className="sr-only">{satisfied ? " — выполнено" : " — не выполнено"}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
