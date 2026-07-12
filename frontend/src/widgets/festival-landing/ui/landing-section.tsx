interface LandingSectionProps {
  /** Anchor id, so the sticky sidebar / hero can deep-link to a section. */
  id?: string;
  title: string;
  subtitle?: string | null;
  children: React.ReactNode;
}

/**
 * Shared wrapper for every main-content landing section.
 *
 * Standardizes the section heading, spacing and scroll-margin so the blocks the
 * organizer enabled read as one coherent page regardless of order.
 */
export function LandingSection({
  id,
  title,
  subtitle,
  children,
}: LandingSectionProps): React.JSX.Element {
  return (
    <section id={id} className="scroll-mt-8">
      <div className="mb-6 space-y-1.5">
        <h2 className="text-pretty text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>
        {subtitle ? <p className="max-w-2xl text-muted-foreground">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}
