/**
 * Duplicate a performance: add a fresh submission to the order and copy the source
 * submission's performance, participants and teachers into it through the existing
 * write endpoints. Pure orchestration over the generated client — no new backend.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { applicationKeys } from "@/entities/application";
import { applicationsAddSubmission } from "@/shared/api/generated/applications/applications";
import type {
  ApplicationResource,
  SubmissionResource,
} from "@/shared/api/generated/model-applications";
import {
  submissionsAddParticipant,
  submissionsAddTeacher,
  submissionsRetrieve,
  submissionsSetPerformance,
} from "@/shared/api/generated/submissions/submissions";

function unwrap<T>(response: unknown): T {
  return (response as { data: { data: T } }).data.data;
}

export function useDuplicatePerformance(applicationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (sourceSubmissionId: string): Promise<void> => {
      const source = unwrap<SubmissionResource>(await submissionsRetrieve(sourceSubmissionId));
      const application = unwrap<ApplicationResource>(
        await applicationsAddSubmission(applicationId),
      );
      const created = application.submissions.at(-1);
      if (!created) {
        return;
      }
      const targetId = created.submissionId;
      if (source.performance) {
        await submissionsSetPerformance(targetId, {
          title: source.performance.title,
          durationSeconds: source.performance.durationSeconds,
          nominationId: source.performance.nominationId,
          disciplineId: source.performance.disciplineId,
          ageCategoryId: source.performance.ageCategoryId,
          participantGroupId: source.performance.participantGroupId,
          participationFormatId: source.performance.participationFormatId,
        });
      }
      for (const participant of source.participants) {
        await submissionsAddParticipant(targetId, {
          firstName: participant.firstName,
          lastName: participant.lastName,
          middleName: participant.middleName,
          birthDate: participant.birthDate,
          gender: participant.gender as "MALE" | "FEMALE",
        });
      }
      for (const teacher of source.teachers) {
        await submissionsAddTeacher(targetId, {
          firstName: teacher.firstName,
          lastName: teacher.lastName,
          middleName: teacher.middleName,
          role: teacher.role,
        });
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}
