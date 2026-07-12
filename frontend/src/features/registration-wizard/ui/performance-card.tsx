import { ChevronDown, ChevronUp, Copy, Trash2 } from "lucide-react";
import { useState } from "react";

import type { Registration } from "@/shared/api/generated/model-public-catalog";
import { Badge, Button, Card, CardContent } from "@/shared/ui";

import { useSubmission } from "../api/hooks";
import { isFullyAdmissible } from "../lib/admission";
import { PerformanceForm } from "./performance-form";

function nameById(
  items: readonly { id: string; name: string }[],
  id: string | undefined,
): string | undefined {
  return id ? items.find((item) => item.id === id)?.name : undefined;
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
  onRemove: () => void;
  onDuplicate: () => void;
  removing: boolean;
  duplicating: boolean;
}): React.JSX.Element {
  const [open, setOpen] = useState(index === 0);
  const { data: submission } = useSubmission(submissionId);

  const performance = submission?.performance ?? null;
  const lead = submission?.participants[0];
  const complete = performance
    ? isFullyAdmissible(registration.admissionRules, {
        nominationId: performance.nominationId,
        disciplineId: performance.disciplineId,
        ageCategoryId: performance.ageCategoryId,
        participantGroupId: performance.participantGroupId,
        participationFormatId: performance.participationFormatId,
      })
    : false;

  return (
    <Card>
      <div className="flex items-center justify-between gap-3 p-4">
        <button
          type="button"
          className="flex flex-1 items-center gap-3 text-left"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? (
            <ChevronUp className="size-4 shrink-0" />
          ) : (
            <ChevronDown className="size-4 shrink-0" />
          )}
          <div>
            <p className="font-medium">
              Выступление #{index + 1}
              {performance?.title ? ` · ${performance.title}` : ""}
            </p>
            <p className="text-sm text-muted-foreground">
              {[
                lead ? `${lead.lastName} ${lead.firstName}` : null,
                nameById(registration.nominations, performance?.nominationId),
                nameById(registration.participationFormats, performance?.participationFormatId),
              ]
                .filter(Boolean)
                .join(" · ") || "Черновик выступления"}
            </p>
          </div>
        </button>
        <div className="flex shrink-0 items-center gap-2">
          {submission?.price ? (
            <Badge variant="success">
              {submission.price.amount} {submission.price.currency}
            </Badge>
          ) : null}
          <Badge variant={complete ? "success" : "neutral"}>
            {complete ? "Заполнено" : "Черновик"}
          </Badge>
          <Button
            variant="ghost"
            size="xs"
            aria-label="Дублировать"
            loading={duplicating}
            onClick={onDuplicate}
          >
            <Copy className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="xs"
            aria-label="Удалить"
            loading={removing}
            onClick={onRemove}
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      </div>
      {open ? (
        <CardContent className="border-t border-border pt-4">
          <PerformanceForm submissionId={submissionId} registration={registration} />
        </CardContent>
      ) : null}
    </Card>
  );
}
