import { ShieldCheck } from "lucide-react";
import { ACCOUNT_CONSENTS, type ConsentDefinition } from "@/shared/consents";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  LoadingState,
  toast,
} from "@/shared/ui";
import { type ConsentEntry, useConsents, useGrantConsent, useWithdrawConsent } from "../api/hooks";

/**
 * The consents this account has given, and the control to take them back.
 *
 * §13.4 of the published policy says consent may be withdrawn at any time, in the
 * cabinet among other channels. This is that channel. Withdrawal is unconditional by
 * law, so there is no confirmation dialog arguing the case and nothing to justify — one
 * button, one request.
 *
 * Two things are deliberately *not* offered here. The consents the account cannot exist
 * without (the terms, and the permission to process the data the account is made of)
 * are shown but not withdrawable: taking them back is deleting the account, which is a
 * different, heavier action with its own confirmation, and pretending a toggle does it
 * would be a lie. And the consents given about a child are not listed: those belong to
 * the child's page, where the person can see whose data they concern.
 */
export function ConsentsCard(): React.JSX.Element {
  const consents = useConsents();
  const withdraw = useWithdrawConsent();
  const grant = useGrantConsent();

  const held = new Map(
    (consents.data ?? [])
      .filter((entry) => entry.subjectParticipantId == null)
      .map((entry) => [entry.consentType, entry]),
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="size-4 text-muted-foreground" aria-hidden="true" />
          Согласия на обработку данных
        </CardTitle>
        <CardDescription>
          Что вы разрешили и на какой редакции текста. Согласие можно отозвать в любое время без
          объяснения причин; отказ от рассылок не влияет на участие в фестивалях.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {consents.isPending ? <LoadingState label="Загружаем согласия…" /> : null}

        {consents.isError ? (
          <Alert variant="danger" role="alert">
            Не удалось загрузить согласия. {consents.error.message}
          </Alert>
        ) : null}

        {consents.isSuccess
          ? ACCOUNT_CONSENTS.map((consent) => (
              <ConsentRow
                key={consent.code}
                consent={consent}
                entry={held.get(consent.code)}
                busy={withdraw.isPending || grant.isPending}
                onWithdraw={async () => {
                  await withdraw.mutateAsync(consent.code);
                  toast.success("Согласие отозвано");
                }}
                onGrant={async () => {
                  await grant.mutateAsync({
                    consentType: consent.code,
                    version: consent.version,
                  });
                  toast.success("Согласие сохранено");
                }}
              />
            ))
          : null}
      </CardContent>
    </Card>
  );
}

/**
 * One consent: its wording, its state, and whatever action is honest for it.
 *
 * A required consent shows what it is and says plainly that withdrawing it means
 * deleting the account, rather than offering a button that would have to refuse.
 */
function ConsentRow({
  consent,
  entry,
  busy,
  onWithdraw,
  onGrant,
}: {
  consent: ConsentDefinition;
  entry: ConsentEntry | undefined;
  busy: boolean;
  onWithdraw: () => Promise<void>;
  onGrant: () => Promise<void>;
}): React.JSX.Element {
  const active = entry != null;

  return (
    <div className="space-y-1.5 border-border/70 border-b pb-4 last:border-b-0 last:pb-0">
      <p className="text-foreground text-sm leading-6">{consent.summary}</p>
      <p className="text-muted-foreground text-xs">
        {active
          ? `Действует${entry?.grantedAt != null ? ` с ${formatDate(entry.grantedAt)}` : ""} · редакция текста ${entry?.version ?? consent.version}`
          : "Не предоставлено"}
      </p>
      {consent.required ? (
        <p className="text-muted-foreground text-xs">
          Обязательно для работы учётной записи. Отзыв означает удаление учётной записи — напишите
          нам, и мы прекратим обработку и удалим данные.
        </p>
      ) : (
        <Button
          variant="outline"
          size="sm"
          loading={busy}
          onClick={() => {
            void (active ? onWithdraw() : onGrant());
          }}
        >
          {active ? "Отозвать согласие" : "Дать согласие"}
        </Button>
      )}
    </div>
  );
}

/** A granted-at instant as a date a person reads, not an ISO string. */
function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString("ru-BY", { day: "numeric", month: "long", year: "numeric" });
}
