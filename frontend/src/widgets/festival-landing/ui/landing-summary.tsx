import { Banknote, CalendarDays, Users } from "lucide-react";
import { formatPeriod } from "@/features/festival-catalog";
import { type FestivalDetail, formatFromPrice, landingCta } from "@/features/festival-landing";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/shared/ui";
import { LandingCtaButton } from "./landing-cta";

interface SummaryRowProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  children: React.ReactNode;
}

function SummaryRow({ icon: Icon, label, children }: SummaryRowProps): React.JSX.Element {
  return (
    <div className="flex items-start gap-3">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <div className="min-w-0 space-y-0.5">
        <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
        <dd className="break-words text-sm font-medium text-foreground">{children}</dd>
      </div>
    </div>
  );
}

interface LandingSummaryProps {
  festival: FestivalDetail;
  applyPath: string;
}

/**
 * The competition summary shown in the sticky desktop sidebar (and, on smaller
 * screens, directly under the hero). A compact recap of the key facts plus the
 * status-driven CTA — a persistent conversion anchor as the visitor scrolls.
 *
 * No "Организатор" row: the organization is named once on this page, in the footer,
 * and it read the *organization's* profile name here — so a festival that overrode
 * its display name showed the overridden one in the footer and the default one in
 * this card, two paragraphs apart.
 */
export function LandingSummary({ festival, applyPath }: LandingSummaryProps): React.JSX.Element {
  const cta = landingCta(festival.status);
  const period = formatPeriod(festival.competitionStart, festival.competitionEnd);
  const price = formatFromPrice(festival.pricing);
  const formatNames = festival.formats.map((format) => format.name);

  return (
    <Card className="overflow-hidden">
      <CardHeader className="border-b">
        <CardTitle className="text-base">Кратко о фестивале</CardTitle>
      </CardHeader>
      <CardContent className="pt-5">
        <dl className="space-y-4">
          {period ? (
            <SummaryRow icon={CalendarDays} label="Даты проведения">
              {period}
            </SummaryRow>
          ) : null}
          {formatNames.length > 0 ? (
            <SummaryRow icon={Users} label="Форматы участия">
              {formatNames.join(", ")}
            </SummaryRow>
          ) : null}
          {price ? (
            <SummaryRow icon={Banknote} label="Стоимость участия">
              {price}
            </SummaryRow>
          ) : null}
        </dl>
      </CardContent>
      <CardFooter className="border-t pt-4">
        <LandingCtaButton cta={cta} applyPath={applyPath} size="md" className="w-full" />
      </CardFooter>
    </Card>
  );
}
