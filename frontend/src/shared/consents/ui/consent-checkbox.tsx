import { useState } from "react";
import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Checkbox } from "@/shared/ui";
import type { ConsentDefinition, ConsentDocument } from "../definitions";

/** Where a box's documents live when it names none: the policy every text cites. */
const DEFAULT_DOCUMENTS: readonly ConsentDocument[] = [
  { to: ROUTES.privacyPolicy, title: "Политика в отношении обработки персональных данных" },
];

/**
 * One consent, asked for the way the law expects it to be asked.
 *
 * The checkbox carries the short statement; the full wording sits behind "Полный текст",
 * collapsed. Both are shown, and that is the point: a consent has to be informed, which
 * a one-line label rarely manages, but a wall of legal prose beside every checkbox is not
 * read at all. Disclosure keeps the full text one click away and present on the page,
 * rather than on some other page the person never opens.
 *
 * The documents themselves are linked *outside* the disclosure, always visible. A box
 * that accepts a contract has to be tickable by someone who read the contract first, and
 * a link they have to expand a panel to find is a link they do not see (LEGAL-003 §3.3).
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
  const documents = consent.documents ?? DEFAULT_DOCUMENTS;
  const disclosureLabel = consent.kind === "acceptance" ? "текст" : "текст согласия";

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
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
          <button
            type="button"
            className="cursor-pointer text-muted-foreground underline hover:text-foreground"
            aria-expanded={expanded}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? `Скрыть полный ${disclosureLabel}` : `Полный ${disclosureLabel}`}
          </button>
          {documents.map((document) => (
            <Link
              key={document.to}
              to={document.to}
              target="_blank"
              rel="noopener"
              className="text-muted-foreground underline hover:text-foreground"
            >
              {document.title}
            </Link>
          ))}
        </div>
        {expanded ? (
          <div className="mt-2 space-y-2 rounded-md border border-border bg-muted/40 p-3 text-foreground/90 text-xs leading-5">
            <p>{consent.text}</p>
            <p className="text-muted-foreground">Редакция текста {consent.version}.</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
