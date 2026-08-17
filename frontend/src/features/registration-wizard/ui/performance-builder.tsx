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
 */
export function PerformanceBuilder({
  applicationId,
  application,
  registration,
}: {
  applicationId: string;
  application: ApplicationResource;
  registration: Registration;
}): React.JSX.Element {
  const addSubmission = useAddSubmission(applicationId);
  const removeSubmission = useRemoveSubmission(applicationId);
  const duplicate = useDuplicatePerformance(applicationId);

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
            onRemove={() => removeSubmission.mutate(ref.submissionId)}
            onDuplicate={() => duplicate.mutate(ref.submissionId)}
          />
        ))
      )}
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
    </div>
  );
}
