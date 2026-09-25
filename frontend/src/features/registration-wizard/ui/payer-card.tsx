import { useEffect } from "react";

import { useSetPayer } from "@/entities/application";
import type {
  ApplicationResource,
  SetPayerRequest,
} from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";
import { useAutosave, useServerDraft } from "@/shared/hooks";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  toast,
} from "@/shared/ui";

/** Mirrors the backend bound on each part of the name (`_LAST_NAME_MAX` and friends). */
const MAX_NAME_PART = 120;

/**
 * Who to name, in the applicant's own terms.
 *
 * Not a stored field: the answer follows from who is entering, and asking the
 * applicant to classify themselves as well as name themselves is a question with one
 * right answer they would have to think about. The organizer reads the name; the
 * capacity is evident from the application it sits on.
 */
const WHO_TO_NAME =
  "Для коллектива — руководитель, для совершеннолетнего участника — он сам, для несовершеннолетнего — законный представитель.";

type Draft = { lastName: string; firstName: string; middleName: string };

function draftOf(payer: ApplicationResource["payer"]): Draft {
  return {
    lastName: payer?.lastName ?? "",
    firstName: payer?.firstName ?? "",
    middleName: payer?.middleName ?? "",
  };
}

function trim(draft: Draft): Draft {
  return {
    lastName: draft.lastName.trim(),
    firstName: draft.firstName.trim(),
    middleName: draft.middleName.trim(),
  };
}

function same(a: Draft, b: Draft): boolean {
  return a.lastName === b.lastName && a.firstName === b.firstName && a.middleName === b.middleName;
}

/**
 * The person the festival's contract for this order is signed with — the payer.
 *
 * Rendered only where the festival asks for one (`collectPayerDetails`), because the
 * backend makes the name a condition of submitting exactly then.
 *
 * Autosaved like every other field in the wizard, but only once the name is one the
 * server would accept: a surname on its own is not a name, and writing on every
 * keystroke would reject the whole way from "И" to "Иванова".
 */
export function PayerCard({
  applicationId,
  application,
  registration,
}: {
  applicationId: string;
  application: ApplicationResource;
  registration: Registration;
}): React.JSX.Element | null {
  const saved = draftOf(application.payer);
  const { mutate, isPending } = useSetPayer(applicationId);
  // Seeded from the order and re-seeded when the order's own payer changes, but never
  // over a name being typed: saving one field echoes the whole application back, and
  // adopting that echo used to wipe the field the applicant had moved on to.
  const [draft, setDraft] = useServerDraft(saved, same);
  const autosave = useAutosave<SetPayerRequest>((body) =>
    mutate(body, { onError: () => toast.error("Не удалось сохранить заказчика") }),
  );

  const typed = trim(draft);
  // Both required parts, or nothing to send: the domain refuses a nameless payer, and
  // there is no way to un-name one — leaving the field blank simply saves nothing.
  const complete = typed.lastName !== "" && typed.firstName !== "";
  const dirty = complete && !same(typed, saved);

  const { schedule, cancel } = autosave;
  useEffect(() => {
    if (!dirty) {
      // Typed and typed back: there is nothing left to tell the server, and a write
      // still waiting would put the abandoned version on the order.
      cancel();
      return;
    }
    schedule({
      lastName: typed.lastName,
      firstName: typed.firstName,
      middleName: typed.middleName || null,
    });
  }, [dirty, typed.lastName, typed.firstName, typed.middleName, schedule, cancel]);

  if (!registration.collectPayerDetails) {
    return null;
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>Заказчик</CardTitle>
          <CardDescription>
            С кем заключается договор и от кого поступает оплата — эти данные нужны для оформления
            документов. {WHO_TO_NAME}
          </CardDescription>
        </div>
        <span className="min-h-5 text-xs text-muted-foreground">
          {isPending ? "Сохраняем…" : ""}
        </span>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-3">
        <Input
          required
          label="Фамилия"
          maxLength={MAX_NAME_PART}
          value={draft.lastName}
          onChange={(event) => setDraft((prev) => ({ ...prev, lastName: event.target.value }))}
          {...(complete ? {} : { description: "Без ФИО заказчика заявку не примут" })}
        />
        <Input
          required
          label="Имя"
          maxLength={MAX_NAME_PART}
          value={draft.firstName}
          onChange={(event) => setDraft((prev) => ({ ...prev, firstName: event.target.value }))}
        />
        <Input
          label="Отчество"
          description="Если есть"
          maxLength={MAX_NAME_PART}
          value={draft.middleName}
          onChange={(event) => setDraft((prev) => ({ ...prev, middleName: event.target.value }))}
        />
      </CardContent>
    </Card>
  );
}
