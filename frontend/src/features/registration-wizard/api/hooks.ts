/**
 * TanStack Query hooks for building one performance (submission).
 *
 * Thin wrappers over the generated Submission content + attachment operations that
 * unwrap the transport envelope and invalidate the affected caches. The Performance
 * Builder consumes these; the projection stays the single source of options.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { applicationKeys } from "@/entities/application";
import type {
  AddParticipantRequest,
  CreditTeacherRequest,
  SetPerformanceRequest,
  SubmissionResource,
  UploadAttachmentRequest,
} from "@/shared/api/generated/model-applications";
import {
  submissionsRemoveAttachment,
  submissionsUploadAttachment,
} from "@/shared/api/generated/submission-attachments/submission-attachments";
import {
  submissionsAddParticipant,
  submissionsAddTeacher,
  submissionsCalculatePrice,
  submissionsRemoveParticipant,
  submissionsRemoveTeacher,
  submissionsRetrieve,
  submissionsSetParticipantMembers,
  submissionsSetPerformance,
} from "@/shared/api/generated/submissions/submissions";

function unwrap<T>(response: unknown): T {
  return (response as { data: { data: T } }).data.data;
}

const submissionKey = (submissionId: string) => ["submission", submissionId] as const;

/** Load one submission (root + performance/participants/teachers/attachments/price). */
export function useSubmission(submissionId: string) {
  return useQuery({
    queryKey: submissionKey(submissionId),
    queryFn: async (): Promise<SubmissionResource> =>
      unwrap<SubmissionResource>(await submissionsRetrieve(submissionId)),
  });
}

function useSubmissionMutation<TArgs>(
  submissionId: string,
  run: (args: TArgs) => Promise<unknown>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (args: TArgs): Promise<SubmissionResource> =>
      unwrap<SubmissionResource>(await run(args)),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: submissionKey(submissionId) });
      void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}

export function useSetPerformance(submissionId: string) {
  return useSubmissionMutation<SetPerformanceRequest>(submissionId, (body) =>
    submissionsSetPerformance(submissionId, body),
  );
}

export function useAddParticipant(submissionId: string) {
  return useSubmissionMutation<AddParticipantRequest>(submissionId, (body) =>
    submissionsAddParticipant(submissionId, body),
  );
}

/** Input for {@link useSetParticipantMembers}: whose roster, and the whole roster. */
export type SetParticipantMembersInput = { participantId: string; members: string[] };

/**
 * Name the people in a collective — the applicant's request for an individual diploma
 * each, on top of the collective's own.
 *
 * The whole roster every time, because that is what the endpoint replaces: an empty
 * list withdraws the request rather than leaving the previous names in place.
 */
export function useSetParticipantMembers(submissionId: string) {
  return useSubmissionMutation<SetParticipantMembersInput>(
    submissionId,
    ({ participantId, members }) =>
      submissionsSetParticipantMembers(submissionId, participantId, { members }),
  );
}

export function useRemoveParticipant(submissionId: string) {
  return useSubmissionMutation<string>(submissionId, (participantId) =>
    submissionsRemoveParticipant(submissionId, participantId),
  );
}

export function useAddTeacher(submissionId: string) {
  return useSubmissionMutation<CreditTeacherRequest>(submissionId, (body) =>
    submissionsAddTeacher(submissionId, body),
  );
}

export function useRemoveTeacher(submissionId: string) {
  return useSubmissionMutation<string>(submissionId, (teacherId) =>
    submissionsRemoveTeacher(submissionId, teacherId),
  );
}

export function useCalculatePrice(submissionId: string) {
  return useSubmissionMutation<void>(submissionId, () => submissionsCalculatePrice(submissionId));
}

export type UploadAttachmentInput = {
  file: File;
  attachmentType: UploadAttachmentRequest["attachmentType"];
  caption?: string;
};

export function useUploadAttachment(submissionId: string) {
  return useSubmissionMutation<UploadAttachmentInput>(submissionId, (body) =>
    // The generated multipart contract types `file` as `string`; the function
    // appends it to FormData verbatim, so a real File is correct at runtime.
    submissionsUploadAttachment(submissionId, {
      file: body.file as unknown as string,
      attachmentType: body.attachmentType,
      caption: body.caption ?? null,
    }),
  );
}

export function useRemoveAttachment(submissionId: string) {
  return useSubmissionMutation<string>(submissionId, (attachmentId) =>
    submissionsRemoveAttachment(submissionId, attachmentId),
  );
}
