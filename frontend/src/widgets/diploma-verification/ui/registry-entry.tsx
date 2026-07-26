import type { VerifiedDiploma } from "@/features/diploma-verification";
import { type DiplomaFactRow, diplomaFactRows } from "@/features/diploma-verification";
import { Badge, Card, CardContent } from "@/shared/ui";

/**
 * One fact of the register entry.
 *
 * Label above value on a phone, label beside value from `sm` up — the two-column
 * form reading an official document invites, without a single table border. Long
 * organization names and work titles wrap rather than overflow (`break-words`),
 * which is why the label column is fixed and the value column is free.
 */
function FactRow({ row }: { row: DiplomaFactRow }): React.JSX.Element {
  return (
    <div className="grid gap-1 py-4 last:pb-0 sm:grid-cols-[11rem_1fr] sm:gap-6">
      {/* Nudged to sit on the value's cap height: the label is 12px against a 16px
          value, so top alignment alone reads as floating. */}
      <dt className="text-muted-foreground text-xs uppercase tracking-wider sm:pt-1">
        {row.label}
      </dt>
      <dd className="min-w-0">
        {row.kind === "identifier" && (
          <span className="font-medium font-mono text-base text-foreground tabular-nums tracking-[0.12em]">
            {row.value}
          </span>
        )}
        {row.kind === "award" && (
          <Badge variant="success" size="md" className="h-auto whitespace-normal px-3 py-1 text-sm">
            {row.value}
          </Badge>
        )}
        {row.kind === "pending" && (
          <span className="text-muted-foreground text-sm italic">{row.value}</span>
        )}
        {row.kind === "text" && (
          <span className="wrap-anywhere font-medium text-base text-foreground">{row.value}</span>
        )}
      </dd>
    </div>
  );
}

/**
 * The register entry itself — the document's recorded facts.
 *
 * Set as a description list with hairline dividers: the vernacular of a document
 * register, where a bordered grid would read as a data dump.
 */
export function RegistryEntry({ diploma }: { diploma: VerifiedDiploma }): React.JSX.Element {
  return (
    <Card>
      <CardContent className="px-6 py-6 sm:px-8">
        <div className="mb-5 space-y-1 border-border border-b pb-4">
          <h2 className="font-semibold text-foreground text-sm uppercase tracking-wider">
            Сведения о документе
          </h2>
          <p className="text-muted-foreground text-xs">
            Зафиксированы в момент выдачи диплома и с тех пор не изменялись.
          </p>
        </div>
        <dl className="divide-y divide-border">
          {diplomaFactRows(diploma).map((row) => (
            <FactRow key={row.key} row={row} />
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
