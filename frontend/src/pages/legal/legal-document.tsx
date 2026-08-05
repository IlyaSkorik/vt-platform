/**
 * The shell both legal pages are written inside.
 *
 * A policy is read in two ways and has to serve both: skimmed for one clause
 * ("what do you do with my child's photo?") and read end to end by someone
 * checking compliance. So the document gets a contents list that jumps, stable
 * per-section anchors that survive being pasted into a letter, and numbered
 * clauses that can be cited — `§12.4` means the same thing on the page as it does
 * in `docs/legal/`.
 *
 * Everything here is structure and typography over design tokens; the wording
 * lives in the page components.
 */

import { cn } from "@/shared/lib/cn";
import { PageContainer } from "@/shared/ui";
import type { LegalRevision } from "./legal-facts";

/** One entry of the contents list, pointing at a `LegalSection` of the same id. */
export type LegalTocEntry = {
  readonly id: string;
  readonly title: string;
};

/**
 * Render a revision's effective date, or say plainly that it has none yet.
 *
 * An unapproved policy is a real state of the world here, and the honest label
 * for it is short: a visitor should not have to infer legal force from silence.
 */
function revisionLabel(revision: LegalRevision): string {
  if (revision.effectiveDate == null) {
    return `Редакция ${revision.version} · проект, не утверждён оператором`;
  }
  const date = new Date(revision.effectiveDate);
  const formatted = Number.isNaN(date.getTime())
    ? revision.effectiveDate
    : date.toLocaleDateString("ru-BY", { day: "numeric", month: "long", year: "numeric" });
  return `Редакция ${revision.version} · действует с ${formatted}`;
}

/** A masthead fact: who the operator is, where to write, which revision this is. */
export type LegalFact = {
  readonly label: string;
  readonly value: React.ReactNode;
};

export function LegalDocument({
  eyebrow,
  title,
  description,
  revision,
  facts,
  toc,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  revision: LegalRevision;
  facts: readonly LegalFact[];
  toc: readonly LegalTocEntry[];
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <PageContainer size="default" className="gap-8 px-4 py-8 sm:px-6 md:py-12">
      <header className="space-y-3">
        <p className="font-medium text-muted-foreground text-xs uppercase tracking-[0.18em]">
          {eyebrow}
        </p>
        <h1 className="font-bold text-2xl text-foreground tracking-tight sm:text-3xl">{title}</h1>
        <p className="max-w-3xl text-muted-foreground text-sm leading-6">{description}</p>
        <p className="text-muted-foreground text-xs">{revisionLabel(revision)}</p>
      </header>

      {/* Who is answerable, and where to write — the two questions a reader has
          before the text itself, so they sit above it rather than in a clause. */}
      <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
        {facts.map((fact) => (
          <div key={fact.label} className="sm:col-span-2 sm:grid sm:grid-cols-subgrid">
            <dt className="text-muted-foreground">{fact.label}</dt>
            <dd className="text-foreground">{fact.value}</dd>
          </div>
        ))}
      </dl>

      <nav
        aria-label="Содержание документа"
        className="rounded-lg border border-border bg-muted/40 p-4 sm:p-5"
      >
        <p className="mb-3 font-semibold text-foreground text-sm">Содержание</p>
        <ol className="grid gap-1.5 text-sm sm:grid-cols-2">
          {toc.map((entry, index) => (
            <li key={entry.id} className="flex gap-2">
              <span className="shrink-0 text-muted-foreground tabular-nums">{index + 1}.</span>
              <a href={`#${entry.id}`} className="text-foreground hover:underline">
                {entry.title}
              </a>
            </li>
          ))}
        </ol>
      </nav>

      {/* `space-y` rather than `gap`: sections are prose, and prose wants a
          consistent vertical rhythm it can be read down, not a grid. */}
      <div className="min-w-0 space-y-8 text-foreground text-sm leading-6">{children}</div>
    </PageContainer>
  );
}

/**
 * One numbered section of the document.
 *
 * `scroll-mt` keeps the heading clear of the sticky application header when a
 * contents link jumps here — without it the anchor lands under the chrome and the
 * reader sees the middle of the section they asked for.
 */
export function LegalSection({
  id,
  number,
  heading,
  children,
}: {
  id: string;
  number: number;
  heading: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <section id={id} className="scroll-mt-24 space-y-3">
      <h2 className="font-semibold text-base text-foreground tracking-tight sm:text-lg">
        {number}. {heading}
      </h2>
      {children}
    </section>
  );
}

/** A subheading inside a section, for documents that need one level more. */
export function LegalSubheading({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <h3 className="pt-1 font-semibold text-foreground text-sm">{children}</h3>;
}

/**
 * One numbered clause — the citable unit of the document.
 *
 * The number is rendered as text rather than a list marker on purpose: clause
 * numbering here is legal identity (`9.4` is referred to by that name in the
 * consent forms and in `docs/legal/`), not presentation, so it must not shift when
 * a clause is inserted above it.
 */
export function LegalClause({
  n,
  children,
}: {
  n: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <p className="text-foreground/90">
      <span className="mr-1.5 font-medium text-muted-foreground tabular-nums">{n}.</span>
      {children}
    </p>
  );
}

/** An unnumbered paragraph — continuation of the clause above it. */
export function LegalParagraph({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <p className="text-foreground/90">{children}</p>;
}

/** A bulleted list inside a clause. */
export function LegalList({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <ul className="ml-1 list-disc space-y-1.5 pl-4 text-foreground/90 marker:text-muted-foreground">
      {children}
    </ul>
  );
}

/**
 * A table, in its own horizontal scroller.
 *
 * Every page primitive carries `min-w-0` precisely so a wide table scrolls itself
 * instead of scrolling the document sideways; this is the container that honours
 * that contract.
 */
export function LegalTable({
  headers,
  children,
  className,
}: {
  headers: readonly string[];
  children: React.ReactNode;
  className?: string;
}): React.JSX.Element {
  return (
    <div className={cn("-mx-1 overflow-x-auto px-1", className)}>
      <table className="w-full min-w-[36rem] border-collapse text-left text-sm">
        <thead>
          <tr className="border-border border-b bg-muted/50">
            {headers.map((header) => (
              <th
                key={header}
                scope="col"
                className="px-3 py-2 font-semibold text-foreground text-xs uppercase tracking-wide"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/70">{children}</tbody>
      </table>
    </div>
  );
}

/** One table row; cells are plain `<td>`s wrapped by `LegalCell`. */
export function LegalRow({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <tr className="align-top">{children}</tr>;
}

export function LegalCell({
  children,
  emphasis = false,
}: {
  children: React.ReactNode;
  emphasis?: boolean;
}): React.JSX.Element {
  return (
    <td
      className={cn(
        "px-3 py-2 text-foreground/90",
        emphasis && "font-medium text-foreground whitespace-nowrap",
      )}
    >
      {children}
    </td>
  );
}

/**
 * A highlighted statement — used where the document says something a reader
 * should not be able to skim past (what the platform does *not* do, what a
 * withdrawal of consent costs).
 */
export function LegalCallout({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <div className="rounded-lg border border-border bg-muted/50 p-4 text-foreground/90">
      {children}
    </div>
  );
}

/** A code-ish inline token: a cookie name, a storage key, a consent identifier. */
export function LegalToken({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em] text-foreground">
      {children}
    </code>
  );
}

/** A `mailto:` link to the operator's contact address. */
export function LegalMail({ address }: { address: string }): React.JSX.Element {
  return (
    <a href={`mailto:${address}`} className="font-medium text-foreground hover:underline">
      {address}
    </a>
  );
}
