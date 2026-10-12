import { ChevronDown, ChevronUp, Copy, Trash2 } from "lucide-react";
import { useState } from "react";

import type { Registration } from "@/shared/api/generated/model-public-catalog";
import { Alert, Badge, Button, Card, CardContent } from "@/shared/ui";

import { useSubmission } from "../api/hooks";
import { isFullyAdmissible, needsAgeComposition } from "../lib/admission";
import { PerformanceForm } from "./performance-form";

function nameById(
  items: readonly { id: string; name: string }[],
  id: string | undefined,
): string | undefined {
  return id ? items.find((item) => item.id === id)?.name : undefined;
}

function nonEmptyText(value: unknown): string | undefined {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : undefined;
}

function leadLabel(lead: unknown): string | undefined {
  if (!lead || typeof lead !== "object") {
    return undefined;
  }
  const record = lead as Record<string, unknown>;
  const displayName = nonEmptyText(record.displayName);
  if (displayName) {
    return displayName;
  }
  const firstName = nonEmptyText(record.firstName);
  const lastName = nonEmptyText(record.lastName);
  const fullName = [lastName, firstName].filter(Boolean).join(" ").trim();
  return fullName.length > 0 ? fullName : undefined;
}

export function PerformanceCard({
  submissionId,
  index,
  registration,
  onRemove,
  onDuplicate,
  removing,
  duplicating,
}: {
  submissionId: string;
  index: number;
  registration: Registration;
  /** ``null`` once the order is paid: its composition is frozen together with its
   * total, so removing a performance would be refused. The number itself stays
   * editable — the card still opens. */
  onRemove: (() => void) | null;
  /** ``null`` when the festival takes one performance per application: duplicating
   * would add a second, so the control is absent rather than present and refused. */
  onDuplicate: (() => void) | null;
  removing: boolean;
  duplicating: boolean;
}): React.JSX.Element {
  const [open, setOpen] = useState(index === 0);
  const { data: submission } = useSubmission(submissionId);

  // Приём по номинации этого номера кончился — сервер его правки больше не примет
  // (`editable` считается тем же правилом, которым он отказывает). На фестивале
  // с остановленным вокалом и работающей хореографией это вопрос про каждый номер
  // отдельно: одна заявка может держать и закрытый, и открытый.
  const frozen = submission != null && !submission.editable;
  const performance = submission?.performance ?? null;
  const lead = submission?.participants[0];
  // A mixed age category is only finished once the applicant has said what ages the
  // group is — the backend refuses the submission without it, so the card should not
  // call it ready either.
  const complete = performance
    ? isFullyAdmissible(registration.admissionRules, {
        nominationId: performance.nominationId,
        disciplineId: performance.disciplineId,
        ageCategoryId: performance.ageCategoryId,
        participantGroupId: performance.participantGroupId,
        participationFormatId: performance.participationFormatId,
      }) &&
      (!needsAgeComposition(registration.ageCategories, performance.ageCategoryId) ||
        performance.ageComposition.trim().length > 0)
    : false;

  return (
    <Card>
      {/* Two lines on a phone, one on a desktop. The controls are ~250 px of badges and
          icon buttons that cannot shrink, and the title is as long as the applicant
          named their act: on one row at 360 px they were pushed off the card and clipped
          away by the layout, so «Удалить» and «Дублировать» could not be reached at all. */}
      <div className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-3 text-left cursor-pointer"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? (
            <ChevronUp className="size-4 shrink-0" />
          ) : (
            <ChevronDown className="size-4 shrink-0" />
          )}
          <div className="min-w-0">
            <p className="font-medium">
              Выступление #{index + 1}
              {performance?.title ? ` · ${performance.title}` : ""}
            </p>
            <p className="text-sm text-muted-foreground">
              {[
                leadLabel(lead),
                nameById(registration.nominations, performance?.nominationId),
                nameById(registration.participationFormats, performance?.participationFormatId),
              ]
                .filter(Boolean)
                .join(" · ") || "Черновик выступления"}
            </p>
          </div>
        </button>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          {submission?.price ? (
            <Badge variant="success">
              {submission.price.amount} {submission.price.currency}
            </Badge>
          ) : null}
          <Badge variant={complete ? "success" : "neutral"}>
            {complete ? "Заполнено" : "Черновик"}
          </Badge>
          {frozen ? <Badge variant="warning">Приём закрыт</Badge> : null}
          {onDuplicate && !frozen ? (
            <Button
              variant="ghost"
              size="xs"
              iconOnly
              aria-label="Дублировать"
              loading={duplicating}
              onClick={onDuplicate}
            >
              <Copy className="size-4" />
            </Button>
          ) : null}
          {onRemove && !frozen ? (
            <Button
              variant="ghost"
              size="xs"
              iconOnly
              aria-label="Удалить"
              loading={removing}
              onClick={onRemove}
            >
              <Trash2 className="size-4" />
            </Button>
          ) : null}
        </div>
      </div>
      {open ? (
        <CardContent className="border-t border-border pt-4">
          {frozen ? (
            <Alert variant="warning">
              <p className="font-medium">Приём заявок по этой номинации закрыт</p>
              <p className="mt-1 text-sm">
                Состав, педагогов и данные номера изменить уже нельзя. Если в них ошибка — напишите
                организатору: правка после закрытия приёма остаётся за ним.
              </p>
            </Alert>
          ) : (
            <PerformanceForm submissionId={submissionId} registration={registration} />
          )}
        </CardContent>
      ) : null}
    </Card>
  );
}
