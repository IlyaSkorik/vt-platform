import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { type ApiError, apiClient, toApiError } from "@/shared/api";
import {
  diplomasAssignmentsList,
  diplomasCreateAssignment,
  diplomasCreateTemplate,
  diplomasDeleteAssignment,
  diplomasGetTemplateLayout,
  diplomasPreviewApplications,
  diplomasPreviewBindings,
  diplomasSaveTemplateLayout,
  diplomasTemplatesList,
} from "@/shared/api/generated/diplomas/diplomas";
import type {
  LayoutResponse,
  PreviewApplication,
  SaveLayoutRequest,
} from "@/shared/api/generated/model-diplomas";
import { defaultBindingForType } from "../model/binding";
import {
  DEFAULT_FIELD_STYLE,
  defaultConfigForType,
  type NominationPartKey,
  type TemplateField,
  type TemplateFieldConfig,
  type TemplateFieldStyle,
  type TemplateFieldTypeId,
} from "../model/constructor";
import type {
  CreateAssignmentPayload,
  CreateTemplatePayload,
  DiplomaAssignment,
  DiplomaTemplate,
  TemplateLayout,
} from "../model/types";
import {
  unwrapAssignmentList,
  unwrapLayout,
  unwrapPreviewApplications,
  unwrapPreviewBindings,
  unwrapTemplateList,
} from "./envelope";
import { diplomaKeys } from "./keys";

/** Merge a persisted (possibly partial/legacy) style onto the defaults. */
function toStyle(style: Partial<TemplateFieldStyle> | undefined): TemplateFieldStyle {
  return { ...DEFAULT_FIELD_STYLE, ...(style ?? {}) };
}

/**
 * Resolve a field's config from the wire: composite fields get their persisted
 * parts/prefix (falling back to the type's defaults for legacy rows that predate
 * config); simple fields get null. An explicit empty `parts` is preserved so a
 * block with no parts selected stays a block.
 */
function toConfig(
  type: TemplateFieldTypeId,
  config: { parts?: string[]; prefix?: string } | undefined,
): TemplateFieldConfig | null {
  const fallback = defaultConfigForType(type);
  if (fallback === null) {
    return null;
  }
  return {
    parts: (config?.parts as NominationPartKey[] | undefined) ?? fallback.parts ?? [],
    prefix: config?.prefix ?? fallback.prefix ?? "",
  };
}

/** Map the wire layout onto the editor's field model. */
function toTemplateLayout(response: LayoutResponse): TemplateLayout {
  return {
    revision: response.revision,
    fields: response.fields.map((field) => {
      const type = field.type as TemplateFieldTypeId;
      // A field is bound if it carries a binding; otherwise it is free text.
      const binding = field.binding || (type === "free_text" ? "" : defaultBindingForType(type));
      const bound = binding !== "";
      return {
        id: field.id,
        page: field.page,
        type,
        binding: bound ? binding : null,
        value: bound ? null : (field.value ?? ""),
        x: field.x,
        y: field.y,
        width: field.width,
        height: field.height,
        style: toStyle(field.style as Partial<TemplateFieldStyle> | undefined),
        config: toConfig(type, field.config),
      };
    }),
  };
}

/** Map the editor's fields onto the whole-layout save request (array order = z-order). */
function toSaveLayoutRequest(fields: TemplateField[]): SaveLayoutRequest {
  return {
    fields: fields.map((field, index) => ({
      page: field.page,
      type: field.type,
      binding: field.binding ?? "",
      value: field.value ?? "",
      x: field.x,
      y: field.y,
      width: field.width,
      height: field.height,
      rotation: 0,
      sortOrder: index,
      style: field.style,
      config: field.config ?? {},
    })),
  };
}

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

async function uploadTemplateDocument(templateId: string, file: File): Promise<void> {
  const body = new FormData();
  body.append("file", file);
  try {
    await apiClient.post(`staff/diplomas/templates/${templateId}/document`, { body });
  } catch (error) {
    throw await toApiError(error);
  }
}

export function useUploadTemplateDocumentMutation(): UseMutationResult<
  void,
  ApiError,
  { templateId: string; file: File }
> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, { templateId: string; file: File }>({
    mutationFn: ({ templateId, file }) => uploadTemplateDocument(templateId, file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: diplomaKeys.templates() });
    },
  });
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

async function fetchLayout(templateId: string, signal?: AbortSignal): Promise<TemplateLayout> {
  const response = await diplomasGetTemplateLayout(templateId, signal ? { signal } : {});
  return toTemplateLayout(unwrapLayout(response.data));
}

async function saveLayout(templateId: string, fields: TemplateField[]): Promise<TemplateLayout> {
  const response = await diplomasSaveTemplateLayout(templateId, toSaveLayoutRequest(fields));
  return toTemplateLayout(unwrapLayout(response.data));
}

export function useTemplateLayout(
  templateId: string | undefined,
): UseQueryResult<TemplateLayout, ApiError> {
  return useQuery<TemplateLayout, ApiError>({
    queryKey: diplomaKeys.layout(templateId ?? ""),
    queryFn: ({ signal }) => fetchLayout(templateId ?? "", signal),
    enabled: Boolean(templateId),
    // The editor owns the working copy after load; don't refetch under it.
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: 0,
  });
}

export function useSaveTemplateLayoutMutation(): UseMutationResult<
  TemplateLayout,
  ApiError,
  { templateId: string; fields: TemplateField[] }
> {
  const queryClient = useQueryClient();
  return useMutation<TemplateLayout, ApiError, { templateId: string; fields: TemplateField[] }>({
    mutationFn: ({ templateId, fields }) => saveLayout(templateId, fields),
    onSuccess: (layout, { templateId }) => {
      queryClient.setQueryData(diplomaKeys.layout(templateId), layout);
    },
  });
}

async function fetchPreviewApplications(
  competitionId: string,
  signal?: AbortSignal,
): Promise<PreviewApplication[]> {
  const response = await diplomasPreviewApplications({ competitionId }, signal ? { signal } : {});
  return unwrapPreviewApplications(response.data);
}

async function fetchPreviewBindings(
  applicationId: string,
  signal?: AbortSignal,
): Promise<Record<string, string>> {
  const response = await diplomasPreviewBindings({ applicationId }, signal ? { signal } : {});
  return unwrapPreviewBindings(response.data);
}

export function usePreviewApplications(
  competitionId: string | undefined,
): UseQueryResult<PreviewApplication[], ApiError> {
  return useQuery<PreviewApplication[], ApiError>({
    queryKey: diplomaKeys.previewApplications(competitionId ?? ""),
    queryFn: ({ signal }) => fetchPreviewApplications(competitionId ?? "", signal),
    enabled: Boolean(competitionId),
    staleTime: 30_000,
  });
}

export function usePreviewBindings(
  applicationId: string | undefined,
): UseQueryResult<Record<string, string>, ApiError> {
  return useQuery<Record<string, string>, ApiError>({
    queryKey: diplomaKeys.previewBindings(applicationId ?? ""),
    queryFn: ({ signal }) => fetchPreviewBindings(applicationId ?? "", signal),
    enabled: Boolean(applicationId),
    staleTime: 30_000,
  });
}
