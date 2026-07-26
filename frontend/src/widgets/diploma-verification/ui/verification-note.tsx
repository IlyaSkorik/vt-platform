import { ShieldCheck } from "lucide-react";
import { formatCheckedAt } from "@/features/diploma-verification";
import { APP_NAME } from "@/shared/config";

/**
 * The check's own record — what was consulted, and when.
 *
 * Quiet by design: it is provenance, not a headline, so it sits outside the card
 * stack on the page background. The timestamp is stamped on the client because it
 * records when *this visitor* consulted the register, which the backend neither
 * knows nor should be asked for.
 */
export function VerificationNote({ checkedAt }: { checkedAt: Date }): React.JSX.Element {
  return (
    <section
      aria-label="Информация о проверке"
      className="flex flex-col items-center gap-3 border-border border-t px-2 pt-6 text-center sm:flex-row sm:items-start sm:gap-4 sm:text-left"
    >
      <ShieldCheck className="size-5 shrink-0 text-muted-foreground sm:mt-0.5" aria-hidden="true" />
      <div className="space-y-2">
        <p className="text-balance text-muted-foreground text-sm">
          Подлинность документа проверена через официальный реестр платформы «{APP_NAME}».
        </p>
        <p className="text-muted-foreground/80 text-xs uppercase tracking-wider">
          Дата проверки{" "}
          <span className="font-medium font-mono text-muted-foreground tabular-nums tracking-normal">
            {formatCheckedAt(checkedAt)}
          </span>
        </p>
      </div>
    </section>
  );
}
