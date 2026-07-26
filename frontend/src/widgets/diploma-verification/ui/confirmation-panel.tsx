import { Check } from "lucide-react";
import { Card } from "@/shared/ui";
import { RegistrySeal } from "./registry-seal";

/**
 * The verdict, stated once and without hedging.
 *
 * The page's thesis: a sealed confirmation that this document is in the register.
 * Deliberately the only element on the page with a tinted surface, so the eye
 * lands on the verdict before the facts that support it.
 */
export function ConfirmationPanel(): React.JSX.Element {
  return (
    <Card className="items-center gap-5 border-success/25 bg-success-surface/40 px-6 py-9 text-center sm:px-10 sm:py-11">
      <RegistrySeal tone="confirmed">
        <Check strokeWidth={3} />
      </RegistrySeal>
      <div className="space-y-3">
        <h2 className="font-bold text-2xl text-foreground tracking-tight sm:text-3xl">
          Диплом подтверждён
        </h2>
        <p className="mx-auto max-w-md text-balance text-base text-foreground/80">
          Подлинность данного диплома успешно подтверждена.
        </p>
        <p className="mx-auto max-w-md text-balance text-muted-foreground text-sm">
          Документ зарегистрирован в официальном реестре платформы.
        </p>
      </div>
    </Card>
  );
}
