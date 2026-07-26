import { cn } from "@/shared/lib";

type SealTone = "confirmed" | "rejected";

const TONES: Record<SealTone, { ring: string; disc: string; field: string }> = {
  confirmed: {
    ring: "border-success/30",
    disc: "bg-success text-success-foreground",
    field: "[--seal-ink:var(--success)]",
  },
  rejected: {
    ring: "border-danger/25",
    disc: "bg-danger text-danger-foreground",
    field: "[--seal-ink:var(--danger)]",
  },
};

interface RegistrySealProps {
  tone: SealTone;
  /** The mark struck into the seal — a check for confirmed, a cross for rejected. */
  children: React.ReactNode;
  className?: string;
}

/**
 * RegistrySeal — the page's one bold element: a struck seal, not a status icon.
 *
 * A document is official because it is sealed, so the confirmation reads as an
 * impression rather than a notification: a solid disc inside a hairline ring,
 * standing on a field of faint concentric rings that echoes the rosette guilloche
 * of security printing. The rings are drawn with a single `repeating-radial-gradient`
 * tinted from the tone's semantic token, so both themes and both tones resolve
 * without a second asset.
 *
 * Purely decorative: the surrounding heading carries the meaning, so the whole
 * mark is hidden from assistive tech.
 */
export function RegistrySeal({ tone, children, className }: RegistrySealProps): React.JSX.Element {
  const { ring, disc, field } = TONES[tone];
  return (
    <div
      aria-hidden="true"
      className={cn("relative flex size-28 items-center justify-center", field, className)}
    >
      <span
        className="pointer-events-none absolute inset-0 rounded-full"
        style={{
          background:
            "repeating-radial-gradient(circle at center, color-mix(in oklab, var(--seal-ink) 38%, transparent) 0 1px, transparent 1px 6px)",
          maskImage:
            "radial-gradient(circle at center, transparent 32%, black 44%, transparent 78%)",
          WebkitMaskImage:
            "radial-gradient(circle at center, transparent 32%, black 44%, transparent 78%)",
        }}
      />
      <span className={cn("absolute inset-4 rounded-full border-2", ring)} />
      <span
        className={cn(
          "relative flex size-14 items-center justify-center rounded-full [&_svg]:size-8",
          disc,
        )}
      >
        {children}
      </span>
    </div>
  );
}
