/**
 * TanStack Query hooks for the Application (order) domain.
 *
 * Thin wrappers over the Orval-generated operations that unwrap the transport
 * envelope (`{ status, data: { data, meta } }`) down to the useful resource and
 * centralise cache invalidation. The wizard and the "My applications" screens
 * consume these rather than the raw generated functions.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  applicationsAddSubmission,
  applicationsCancel,
  applicationsCreate,
  applicationsList,
  applicationsRecordConsents,
  applicationsRemoveReceipt,
  applicationsRemoveService,
  applicationsRemoveSubmission,
  applicationsRequestPayment,
  applicationsRetrieve,
  applicationsSelectOrganization,
  applicationsSelectService,
  applicationsSubmit,
  applicationsUploadReceipt,
} from "@/shared/api/generated/applications/applications";
import type {
  ApplicationResource,
  ApplicationSummaryResource,
  AttachmentTypeEnum,
  RecordConsentsRequest,
  SelectEducationalOrganizationRequest,
  SelectServiceRequest,
  SubmissionResource,
} from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";
import { getRegistration } from "@/shared/api/generated/public-catalog/public-catalog";
import {
  submissionsRemoveAttachment,
  submissionsUploadAttachment,
} from "@/shared/api/generated/submission-attachments/submission-attachments";
import { submissionsRetrieve } from "@/shared/api/generated/submissions/submissions";

import { applicationKeys } from "./keys";

/**
 * Unwrap the transport envelope to the inner resource.
 *
 * Generated operations are typed as a `success | problem` union, but the shared
 * mutator throws a typed `ApiError` on every non-2xx response — so a value that
 * *resolves* is always the success envelope `{ data: { data: T } }`.
 */
function unwrap<T>(response: unknown): T {
  return (response as { data: { data: T } }).data.data;
}

/** List the current applicant's applications, optionally filtered to a status. */
export function useMyApplications(status?: string) {
  return useQuery({
    queryKey: applicationKeys.list(status),
    queryFn: async (): Promise<ApplicationSummaryResource[]> => {
      const response = await applicationsList(status ? { status } : undefined);
      return unwrap<ApplicationSummaryResource[]>(response);
    },
  });
}

/**
 * The single Registration projection for a competition — everything the wizard
 * renders (taxonomy, admission rules, services, required consents, upload rules,
 * deadlines, availability) from one request.
 */
export function useRegistration(competitionId: string | undefined) {
  return useQuery({
    queryKey: ["registration", competitionId ?? "unknown"],
    queryFn: async (): Promise<Registration> =>
      unwrap<Registration>(await getRegistration(competitionId as string)),
    enabled: Boolean(competitionId),
  });
}

/** Retrieve one application in full. */
export function useApplication(applicationId: string | undefined) {
  return useQuery({
    queryKey: applicationKeys.detail(applicationId ?? "unknown"),
    queryFn: async (): Promise<ApplicationResource> => {
      const response = await applicationsRetrieve(applicationId as string);
      return unwrap<ApplicationResource>(response);
    },
    enabled: Boolean(applicationId),
  });
}

function useInvalidateApplication() {
  const queryClient = useQueryClient();
  return (applicationId?: string) => {
    void queryClient.invalidateQueries({ queryKey: applicationKeys.lists() });
    if (applicationId) {
      void queryClient.invalidateQueries({ queryKey: applicationKeys.detail(applicationId) });
    }
  };
}

/** Create a new DRAFT application for a competition. */
export function useCreateApplication() {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (competitionId: string): Promise<ApplicationResource> => {
      const response = await applicationsCreate({ competitionId });
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: (application) => invalidate(application.id),
  });
}

/** Add a fresh draft submission (performance) to an application. */
export function useAddSubmission(applicationId: string) {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (): Promise<ApplicationResource> => {
      const response = await applicationsAddSubmission(applicationId);
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: () => invalidate(applicationId),
  });
}

/** Detach (and cancel) a submission from the application. */
export function useRemoveSubmission(applicationId: string) {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (submissionId: string): Promise<ApplicationResource> => {
      const response = await applicationsRemoveSubmission(applicationId, submissionId);
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: () => invalidate(applicationId),
  });
}

/** Select an additional service on the application. */
export function useSelectService(applicationId: string) {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (body: SelectServiceRequest): Promise<ApplicationResource> => {
      const response = await applicationsSelectService(applicationId, body);
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: () => invalidate(applicationId),
  });
}

/** Remove a previously selected additional service. */
export function useRemoveService(applicationId: string) {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (serviceId: string): Promise<ApplicationResource> => {
      const response = await applicationsRemoveService(applicationId, serviceId);
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: () => invalidate(applicationId),
  });
}

/** Record the accepted consents on the application. */
export function useRecordConsents(applicationId: string) {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (body: RecordConsentsRequest): Promise<ApplicationResource> => {
      const response = await applicationsRecordConsents(applicationId, body);
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: () => invalidate(applicationId),
  });
}

/** Select the applicant's educational organization for the application. */
export function useSelectOrganization(applicationId: string) {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (
      body: SelectEducationalOrganizationRequest,
    ): Promise<ApplicationResource> => {
      const response = await applicationsSelectOrganization(applicationId, body);
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: () => invalidate(applicationId),
  });
}

/** Submit (place) the order. */
export function useSubmitApplication(applicationId: string) {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (): Promise<ApplicationResource> => {
      const response = await applicationsSubmit(applicationId);
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: () => invalidate(applicationId),
  });
}

/** Move an approved order to awaiting payment. */
export function useRequestPayment(applicationId: string) {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (): Promise<ApplicationResource> => {
      const response = await applicationsRequestPayment(applicationId);
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: () => invalidate(applicationId),
  });
}

/**
 * Attach one more order-level payment receipt (multipart).
 *
 * Adds rather than replaces: an order's fee is regularly settled by several
 * transfers, so each upload is another slip, not a correction of the last.
 */
export function useUploadReceipt(applicationId: string) {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (file: File): Promise<ApplicationResource> => {
      // The generated multipart contract types `file` as `string`; a real File is
      // appended to FormData verbatim, so it is correct at runtime.
      const response = await applicationsUploadReceipt(applicationId, {
        file: file as unknown as string,
      });
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: () => invalidate(applicationId),
  });
}

/** Take back one of the order's payment receipts (the wrong file, or a duplicate). */
export function useRemoveReceipt(applicationId: string) {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (receiptId: string): Promise<ApplicationResource> => {
      const response = await applicationsRemoveReceipt(applicationId, receiptId);
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: () => invalidate(applicationId),
  });
}

/**
 * Load one submission in full (performance, participants, teachers, attachments).
 *
 * The order screens need this for the attachments a submission carries; the
 * Performance Builder keeps its own copy of the same query under its own key.
 */
export function useSubmissionDetail(submissionId: string | undefined) {
  return useQuery({
    queryKey: applicationKeys.submission(submissionId ?? "unknown"),
    queryFn: async (): Promise<SubmissionResource> =>
      unwrap<SubmissionResource>(await submissionsRetrieve(submissionId as string)),
    enabled: Boolean(submissionId),
  });
}

/**
 * Invalidate everything a change to a submission's attachments can be seen through:
 * this entity's copy, the Performance Builder's, and the order (whose cached
 * per-performance prices depend on whether a benefit is claimed).
 */
function useInvalidateSubmission(submissionId: string) {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: applicationKeys.submission(submissionId) });
    void queryClient.invalidateQueries({ queryKey: ["submission", submissionId] });
    void queryClient.invalidateQueries({ queryKey: applicationKeys.all });
  };
}

/** Attach a file of the given kind to a submission (multipart). */
export function useUploadSubmissionAttachment(submissionId: string) {
  const invalidate = useInvalidateSubmission(submissionId);
  return useMutation({
    mutationFn: async (input: {
      file: File;
      attachmentType: AttachmentTypeEnum;
      caption?: string | undefined;
    }): Promise<SubmissionResource> => {
      // The generated multipart contract types `file` as `string`; a real File is
      // appended to FormData verbatim, so it is correct at runtime.
      const response = await submissionsUploadAttachment(submissionId, {
        file: input.file as unknown as string,
        attachmentType: input.attachmentType,
        caption: input.caption ?? null,
      });
      return unwrap<SubmissionResource>(response);
    },
    onSuccess: invalidate,
  });
}

/** Detach one attachment from a submission. */
export function useRemoveSubmissionAttachment(submissionId: string) {
  const invalidate = useInvalidateSubmission(submissionId);
  return useMutation({
    mutationFn: async (attachmentId: string): Promise<SubmissionResource> =>
      unwrap<SubmissionResource>(await submissionsRemoveAttachment(submissionId, attachmentId)),
    onSuccess: invalidate,
  });
}

/** Cancel the order. */
export function useCancelApplication(applicationId: string) {
  const invalidate = useInvalidateApplication();
  return useMutation({
    mutationFn: async (): Promise<ApplicationResource> => {
      const response = await applicationsCancel(applicationId);
      return unwrap<ApplicationResource>(response);
    },
    onSuccess: () => invalidate(applicationId),
  });
}
