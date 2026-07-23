import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { ApiError } from "@/shared/api";
import {
  diplomasAssignmentsList,
  diplomasCreateAssignment,
  diplomasCreateTemplate,
  diplomasDeleteAssignment,
  diplomasTemplatesList,
} from "@/shared/api/generated/diplomas/diplomas";
import type {
  CreateAssignmentPayload,
  CreateTemplatePayload,
  DiplomaAssignment,
  DiplomaTemplate,
} from "../model/types";
import { unwrapAssignmentList, unwrapTemplateList } from "./envelope";
import { diplomaKeys } from "./keys";

async function fetchTemplates(signal?: AbortSignal): Promise<DiplomaTemplate[]> {
  const response = await diplomasTemplatesList(signal ? { signal } : {});
  return unwrapTemplateList(response.data);
}

async function fetchAssignments(signal?: AbortSignal): Promise<DiplomaAssignment[]> {
  const response = await diplomasAssignmentsList(signal ? { signal } : {});
  return unwrapAssignmentList(response.data);
}

export function useDiplomaTemplates(): UseQueryResult<DiplomaTemplate[], ApiError> {
  return useQuery<DiplomaTemplate[], ApiError>({
    queryKey: diplomaKeys.templates(),
    queryFn: ({ signal }) => fetchTemplates(signal),
    staleTime: 30_000,
  });
}

export function useCreateTemplateMutation(): UseMutationResult<
  void,
  ApiError,
  CreateTemplatePayload
> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, CreateTemplatePayload>({
    mutationFn: async (payload) => {
      await diplomasCreateTemplate(payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: diplomaKeys.templates() });
    },
  });
}

export interface DiplomaTemplateQuery {
  template: DiplomaTemplate | undefined;
  isLoading: boolean;
  isError: boolean;
  error: ApiError | null;
  refetch: () => void;
}

/**
 * A single template, selected from the library list (react-query caches it).
 * A dedicated GET endpoint can replace this later without changing callers.
 */
export function useDiplomaTemplate(templateId: string | undefined): DiplomaTemplateQuery {
  const query = useDiplomaTemplates();
  return {
    template: (query.data ?? []).find((item) => item.id === templateId),
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: () => {
      void query.refetch();
    },
  };
}

export function useDiplomaAssignments(): UseQueryResult<DiplomaAssignment[], ApiError> {
  return useQuery<DiplomaAssignment[], ApiError>({
    queryKey: diplomaKeys.assignments(),
    queryFn: ({ signal }) => fetchAssignments(signal),
    staleTime: 15_000,
  });
}

export function useCreateAssignmentMutation(): UseMutationResult<
  void,
  ApiError,
  CreateAssignmentPayload
> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, CreateAssignmentPayload>({
    mutationFn: async (payload) => {
      await diplomasCreateAssignment(payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: diplomaKeys.assignments() });
      // Usage counts on templates change when an assignment is added.
      void queryClient.invalidateQueries({ queryKey: diplomaKeys.templates() });
    },
  });
}

export function useDeleteAssignmentMutation(): UseMutationResult<void, ApiError, string> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: async (assignmentId) => {
      await diplomasDeleteAssignment(assignmentId);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: diplomaKeys.assignments() });
      void queryClient.invalidateQueries({ queryKey: diplomaKeys.templates() });
    },
  });
}
