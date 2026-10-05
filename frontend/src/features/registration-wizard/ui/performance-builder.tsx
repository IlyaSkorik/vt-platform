import { Plus } from "lucide-react";

import { useAddSubmission, useRemoveSubmission } from "@/entities/application";
import type { ApplicationResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";
import { Button } from "@/shared/ui";

import { useDuplicatePerformance } from "../api/duplicate";
import { PerformanceCard } from "./performance-card";

/**
 * The Performance Builder: one collapsible card per performance (submission), with
 * add / remove / duplicate. Each card's form is driven entirely by the Registration
 * projection; a performance the festival priced carries that price as a badge in its
 * header, and one it did not carries nothing.
 *
 * A festival that judges one act per entrant turns ``allowMultiplePerformances`` off,
 * and then add and duplicate are *absent* rather than disabled — the same rule the
 * Applications context enforces on the endpoint, so the button that is gone is
 * exactly the request that would have been refused. It comes back when the order is
 * empty: removing the one performance has to leave a way to enter another.
 *
 * ``composable`` is the same idea one level up: a paid order has a frozen total, so
 * adding, duplicating and removing performances are gone, while the performances
 * themselves stay open — the surname on a diploma is still worth fixing.
 */
export function PerformanceBuilder({
  applicationId,
  application,
  registration,
  composable = true,
}: {
  applicationId: string;
  application: ApplicationResource;
  registration: Registration;
  composable?: boolean;
}): React.JSX.Element {
  const addSubmission = useAddSubmission(applicationId);
  const removeSubmission = useRemoveSubmission(applicationId);
  const duplicate = useDuplicatePerformance(applicationId);
  const canAdd =
    composable && (registration.allowMultiplePerformances || application.submissions.length === 0);

  return (
    <div className="flex flex-col gap-4">
      {application.submissions.length === 0 ? (
        <p className="text-sm text-muted-foreground">Добавьте хотя бы одно выступление.</p>
      ) : (
        application.submissions.map((ref, index) => (
          <PerformanceCard
            key={ref.submissionId}
            submissionId={ref.submissionId}
            index={index}
            registration={registration}
            removing={removeSubmission.isPending}
            duplicating={duplicate.isPending}
            onRemove={composable ? () => removeSubmission.mutate(ref.submissionId) : null}
            onDuplicate={
              composable && registration.allowMultiplePerformances
                ? () => duplicate.mutate(ref.submissionId)
                : null
            }
          />
        ))
      )}
      {canAdd ? (
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            loading={addSubmission.isPending}
            onClick={() => addSubmission.mutate()}
          >
            <Plus className="size-4" />
            Добавить выступление
          </Button>
        </div>
      ) : composable ? (
        <p className="text-sm text-muted-foreground">
          Фестиваль принимает одно выступление в заявке.
        </p>
      ) : null}
    </div>
  );
}
