import { useState } from "react";
import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Checkbox } from "@/shared/ui";
import type { ConsentDefinition } from "../definitions";

/**
 * One consent, asked for the way the law expects it to be asked.
 *
 * The checkbox carries the short statement; the full wording sits behind "Полный текст
 * согласия", collapsed. Both are shown, and that is the point: a consent has to be
 * informed, which a one-line label rarely manages, but a wall of legal prose beside
 * every checkbox is not read at all. Disclosure keeps the full text one click away and
 * present on the page, rather than on some other page the person never opens.
 *
 * Nothing is pre-ticked. A consent that starts checked is not freely given, whatever
 * the label says.
 */
export function ConsentCheckbox({
  consent,
  checked,
  onChange,
  error,
  disabled = false,
}: {
  consent: ConsentDefinition;
  checked: boolean;
  onChange: (checked: boolean) => void;
  error?: string | undefined;
  disabled?: boolean;
}): React.JSX.Element {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="space-y-1.5">
      <Checkbox
        checked={checked}
        disabled={disabled}
        error={error}
        onCheckedChange={(next) => onChange(next === true)}
        label={
          <span className="text-sm leading-6">
            {consent.summary}
            {consent.required ? null : (
              <span className="ml-1 text-muted-foreground text-xs">(по желанию)</span>
            )}
          </span>
        }
      />
      <div className="pl-7">
        <button
          type="button"
          className="cursor-pointer text-muted-foreground text-xs underline hover:text-foreground"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? "Скрыть полный текст" : "Полный текст согласия"}
        </button>
        {expanded ? (
          <div className="mt-2 space-y-2 rounded-md border border-border bg-muted/40 p-3 text-foreground/90 text-xs leading-5">
            <p>{consent.text}</p>
            <p className="text-muted-foreground">
              Редакция текста {consent.version}. См.{" "}
              <Link to={ROUTES.privacyPolicy} className="underline hover:text-foreground">
                Политику в отношении обработки персональных данных
              </Link>
              .
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
