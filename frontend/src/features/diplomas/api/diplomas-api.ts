import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { type ApiError, apiClient, toApiError, uploadTimeoutMs } from "@/shared/api";
import {
  diplomasAssignmentsList,
  diplomasCreateAssignment,
  diplomasCreateTemplate,
  diplomasDeleteAssignment,
  diplomasGenerateDocuments,
  diplomasGenerationArchive,
  diplomasGetPrintJob,
  diplomasGetTemplateLayout,
  diplomasPreviewApplications,
  diplomasPreviewBindings,
  diplomasPrintPackageSummary,
  diplomasRegistryList,
  diplomasSaveTemplateLayout,
  diplomasStartPrintPackage,
  diplomasTemplatesList,
} from "@/shared/api/generated/diplomas/diplomas";
import type {
  DiplomaResponse,
  GenerateDocumentsRequestDocumentTypeEnum,
  GenerateDocumentsResponse,
  GenerationRunResponse,
  LayoutResponse,
  PreviewApplication,
  PrintJobResponse,
  PrintPackageSummaryResponse,
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
import type { DocumentType } from "../model/document-types";
import type {
  CreateAssignmentPayload,
  CreateTemplatePayload,
  DiplomaAssignment,
  DiplomaTemplate,
  TemplateLayout,
} from "../model/types";
import {
  unwrapAssignmentList,
  unwrapDiplomaList,
  unwrapGeneratedDocuments,
  unwrapGenerationRuns,
  unwrapLayout,
  unwrapPreviewApplications,
  unwrapPreviewBindings,
  unwrapPrintJob,
  unwrapPrintSummary,
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
  // The whole library in one read; callers narrow by `type` client-side, which
  // keeps a single cache entry serving both the diploma and thank-you slots.
  const response = await diplomasTemplatesList(undefined, signal ? { signal } : {});
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
    await apiClient.post(`staff/diplomas/templates/${templateId}/document`, {
      body,
      timeout: uploadTimeoutMs(body),
    });
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
  documentType: DocumentType,
  signal?: AbortSignal,
): Promise<Record<string, string>> {
  const response = await diplomasPreviewBindings(
    { applicationId, documentType },
    signal ? { signal } : {},
  );
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

/**
 * Resolved values for one application, formatted for a document kind.
 *
 * The kind is part of the read, not a display concern: a diploma credits a teacher
 * as "Педагог: ФИО" while a thank-you letter prints the name alone, and the editor
 * must preview whatever will actually print. It is therefore part of the cache key.
 */
export function usePreviewBindings(
  applicationId: string | undefined,
  documentType: DocumentType = "DIPLOMA",
): UseQueryResult<Record<string, string>, ApiError> {
  return useQuery<Record<string, string>, ApiError>({
    queryKey: diplomaKeys.previewBindings(applicationId ?? "", documentType),
    queryFn: ({ signal }) => fetchPreviewBindings(applicationId ?? "", documentType, signal),
    enabled: Boolean(applicationId),
    staleTime: 30_000,
  });
}

// --- Print package (mass generation) ---------------------------------------

async function fetchRegistry(
  competitionId: string,
  signal?: AbortSignal,
): Promise<DiplomaResponse[]> {
  const response = await diplomasRegistryList({ competitionId }, signal ? { signal } : {});
  return unwrapDiplomaList(response.data);
}

/** A competition's existing diplomas — used for the generation summary counts. */
export function useDiplomaRegistry(
  competitionId: string | undefined,
): UseQueryResult<DiplomaResponse[], ApiError> {
  return useQuery<DiplomaResponse[], ApiError>({
    queryKey: diplomaKeys.registry(competitionId ?? ""),
    queryFn: ({ signal }) => fetchRegistry(competitionId ?? "", signal),
    enabled: Boolean(competitionId),
    staleTime: 15_000,
  });
}

async function fetchPrintSummary(
  competitionId: string,
  signal?: AbortSignal,
): Promise<PrintPackageSummaryResponse> {
  const response = await diplomasPrintPackageSummary({ competitionId }, signal ? { signal } : {});
  return unwrapPrintSummary(response.data);
}

/** Per-nomination print-package summary (template + counts) for a competition. */
export function usePrintPackageSummary(
  competitionId: string | undefined,
): UseQueryResult<PrintPackageSummaryResponse, ApiError> {
  return useQuery<PrintPackageSummaryResponse, ApiError>({
    queryKey: diplomaKeys.printSummary(competitionId ?? ""),
    queryFn: ({ signal }) => fetchPrintSummary(competitionId ?? "", signal),
    enabled: Boolean(competitionId),
    staleTime: 10_000,
  });
}

/** Start a print-package generation for chosen nominations; returns the job. */
export function useStartPrintPackageMutation(): UseMutationResult<
  PrintJobResponse,
  ApiError,
  { competitionId: string; categoryIds: string[]; force?: boolean }
> {
  const queryClient = useQueryClient();
  return useMutation<
    PrintJobResponse,
    ApiError,
    { competitionId: string; categoryIds: string[]; force?: boolean }
  >({
    mutationFn: async ({ competitionId, categoryIds, force = false }) => {
      const response = await diplomasStartPrintPackage({ competitionId, categoryIds, force });
      return unwrapPrintJob(response.data);
    },
    onSuccess: (_job, { competitionId }) => {
      // New diplomas may have been created — refresh the summary counts.
      void queryClient.invalidateQueries({ queryKey: diplomaKeys.printSummary(competitionId) });
      void queryClient.invalidateQueries({ queryKey: diplomaKeys.registry(competitionId) });
      // The archive gains its line when the job completes, not now — this drops the
      // stale history so opening the archive after the run reads it fresh.
      void queryClient.invalidateQueries({ queryKey: diplomaKeys.generationArchives() });
    },
  });
}

export interface GenerateDocumentsPayload {
  competitionId: string;
  categoryIds: string[];
  documentType: DocumentType;
  force?: boolean;
  /** Also archive the run's documents into one ZIP for offline printing (`zipUrl`). */
  bundle?: boolean;
  /**
   * Show the documents to the participants (default). Off for a run that only
   * prepares sheets to print: they are generated and stored, but stay out of the
   * cabinets until a later run publishes them. Never withdraws a publication.
   */
  publish?: boolean;
}

/**
 * Generate non-registry documents (thank-you letters) for chosen nominations.
 *
 * Synchronous, unlike the diploma print package: there is no number to reserve, so
 * the response already carries the outcome (and the archive, when asked for) and
 * there is no job to poll. Each nomination uses its own assigned template of the kind.
 * `publish` and `bundle` are independent — see {@link GenerateDocumentsPayload}.
 */
export function useGenerateDocumentsMutation(): UseMutationResult<
  GenerateDocumentsResponse,
  ApiError,
  GenerateDocumentsPayload
> {
  const queryClient = useQueryClient();
  return useMutation<GenerateDocumentsResponse, ApiError, GenerateDocumentsPayload>({
    mutationFn: async ({
      competitionId,
      categoryIds,
      documentType,
      force = false,
      bundle = false,
      publish = true,
    }) => {
      const response = await diplomasGenerateDocuments({
        competitionId,
        categoryIds,
        documentType: documentType as GenerateDocumentsRequestDocumentTypeEnum,
        force,
        bundle,
        publish,
      });
      return unwrapGeneratedDocuments(response.data);
    },
    onSuccess: (_summary, { competitionId }) => {
      void queryClient.invalidateQueries({ queryKey: diplomaKeys.printSummary(competitionId) });
      // A synchronous run: the archive already holds its line.
      void queryClient.invalidateQueries({ queryKey: diplomaKeys.generationArchives() });
    },
  });
}

async function fetchGenerationArchive(
  competitionId: string,
  signal?: AbortSignal,
): Promise<GenerationRunResponse[]> {
  const response = await diplomasGenerationArchive(
    competitionId ? { competitionId } : undefined,
    signal ? { signal } : {},
  );
  return unwrapGenerationRuns(response.data);
}

/**
 * The generation history: completed runs of every document kind, newest first.
 *
 * Invalidated by both generation actions, since a run is what adds a line to it.
 * Passing a competition narrows the history to that competition.
 */
export function useGenerationArchive(
  competitionId?: string,
): UseQueryResult<GenerationRunResponse[], ApiError> {
  return useQuery<GenerationRunResponse[], ApiError>({
    queryKey: diplomaKeys.generationArchive(competitionId ?? ""),
    queryFn: ({ signal }) => fetchGenerationArchive(competitionId ?? "", signal),
    staleTime: 10_000,
  });
}

async function fetchPrintJob(jobId: string, signal?: AbortSignal): Promise<PrintJobResponse> {
  const response = await diplomasGetPrintJob(jobId, signal ? { signal } : {});
  return unwrapPrintJob(response.data);
}

/** Poll a print-package job while it is pending/running; stop once it settles. */
export function usePrintJob(jobId: string | undefined): UseQueryResult<PrintJobResponse, ApiError> {
  return useQuery<PrintJobResponse, ApiError>({
    queryKey: diplomaKeys.printJob(jobId ?? ""),
    queryFn: ({ signal }) => fetchPrintJob(jobId ?? "", signal),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "PENDING" || status === "RUNNING" ? 2500 : false;
    },
  });
}
