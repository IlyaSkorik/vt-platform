import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { type ApiError, apiClient, toApiError } from "@/shared/api";
import {
  addContact,
  addDocument,
  addRegulation,
  archiveCompetition,
  getCompetition,
  listCompetitions,
  makeRegulationCurrent,
  markCompetitionConfigured,
  markCompetitionReady,
  openRegistration,
  postCompetition,
  publishCompetition,
  publishDocument,
  removeContact,
  removeDocument,
  removeRegulation,
  unpublishDocument,
  updateBranding,
  updateCompetition,
  updateDocument,
} from "@/shared/api/generated/competitions/competitions";
import type {
  AddContact,
  AddDocument,
  AddRegulation,
  CompetitionDetail,
  CompetitionSummary,
  CreateCompetition,
  PatchedUpdateCompetitionBranding,
  PatchedUpdateCompetitionGeneralInformation,
  PatchedUpdateDocument,
} from "@/shared/api/generated/model-competitions";
import { cacheOrganizerId } from "../lib/organizer-id";
import { unwrapCompetitionDetail, unwrapCompetitionList } from "./envelope";
import { competitionKeys } from "./keys";

function toSummary(detail: CompetitionDetail): CompetitionSummary {
  return {
    id: detail.id,
    title: detail.title,
    season: detail.season,
    status: detail.status,
    organizerId: detail.organizerId,
    description: detail.description,
    createdAt: detail.createdAt,
    updatedAt: detail.updatedAt,
    version: detail.version,
  };
}

async function fetchCompetitions(signal?: AbortSignal): Promise<CompetitionSummary[]> {
  const response = await listCompetitions(signal ? { signal } : {});
  const items = unwrapCompetitionList(response.data);
  const organizerId = items[0]?.organizerId;
  if (organizerId) {
    cacheOrganizerId(organizerId);
  }
  return items;
}

async function fetchCompetition(
  competitionId: string,
  signal?: AbortSignal,
): Promise<CompetitionDetail> {
  const response = await getCompetition(competitionId, signal ? { signal } : {});
  const detail = unwrapCompetitionDetail(response.data);
  cacheOrganizerId(detail.organizerId);
  return detail;
}

async function createDraftCompetition(payload: CreateCompetition): Promise<CompetitionDetail> {
  const response = await postCompetition(payload);
  const detail = unwrapCompetitionDetail(response.data);
  cacheOrganizerId(detail.organizerId);
  return detail;
}

async function patchGeneralInformation(
  competitionId: string,
  payload: PatchedUpdateCompetitionGeneralInformation,
): Promise<CompetitionDetail> {
  const response = await updateCompetition(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function patchBranding(
  competitionId: string,
  payload: PatchedUpdateCompetitionBranding,
): Promise<CompetitionDetail> {
  const response = await updateBranding(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function uploadPoster(competitionId: string, file: File): Promise<CompetitionDetail> {
  const body = new FormData();
  body.append("file", file);
  try {
    const response = await apiClient
      .post(`competitions/${competitionId}/branding/poster`, { body })
      .json<unknown>();
    return unwrapCompetitionDetail(response);
  } catch (error) {
    throw await toApiError(error);
  }
}

async function uploadRegulationPdf(competitionId: string, file: File): Promise<string> {
  const body = new FormData();
  body.append("file", file);
  try {
    const response = await apiClient
      .post(`competitions/${competitionId}/uploads/regulation`, { body })
      .json<{ data?: { fileReference?: string } }>();
    const fileReference = response.data?.fileReference?.trim();
    if (!fileReference) {
      throw new Error("Unexpected regulation upload response.");
    }
    return fileReference;
  } catch (error) {
    throw await toApiError(error);
  }
}

async function uploadDocumentFile(competitionId: string, file: File): Promise<string> {
  const body = new FormData();
  body.append("file", file);
  try {
    const response = await apiClient
      .post(`competitions/${competitionId}/uploads/document`, { body })
      .json<{ data?: { fileReference?: string } }>();
    const fileReference = response.data?.fileReference?.trim();
    if (!fileReference) {
      throw new Error("Unexpected document upload response.");
    }
    return fileReference;
  } catch (error) {
    throw await toApiError(error);
  }
}

async function createDocument(
  competitionId: string,
  payload: AddDocument,
): Promise<CompetitionDetail> {
  const response = await addDocument(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function patchDocument(
  competitionId: string,
  documentId: string,
  payload: PatchedUpdateDocument,
): Promise<CompetitionDetail> {
  const response = await updateDocument(competitionId, documentId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function deleteDocument(
  competitionId: string,
  documentId: string,
): Promise<CompetitionDetail> {
  const response = await removeDocument(competitionId, documentId);
  return unwrapCompetitionDetail(response.data);
}

async function setDocumentPublished(
  competitionId: string,
  documentId: string,
  published: boolean,
): Promise<CompetitionDetail> {
  const response = published
    ? await publishDocument(competitionId, documentId)
    : await unpublishDocument(competitionId, documentId);
  return unwrapCompetitionDetail(response.data);
}

async function publishRegulation(
  competitionId: string,
  payload: AddRegulation,
): Promise<CompetitionDetail> {
  const response = await addRegulation(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function setCurrentRegulation(
  competitionId: string,
  regulationId: string,
): Promise<CompetitionDetail> {
  const response = await makeRegulationCurrent(competitionId, regulationId);
  return unwrapCompetitionDetail(response.data);
}

async function deleteRegulation(
  competitionId: string,
  regulationId: string,
): Promise<CompetitionDetail> {
  const response = await removeRegulation(competitionId, regulationId);
  return unwrapCompetitionDetail(response.data);
}

async function publish(competitionId: string): Promise<CompetitionDetail> {
  const response = await publishCompetition(competitionId);
  return unwrapCompetitionDetail(response.data);
}

async function markConfigured(competitionId: string): Promise<CompetitionDetail> {
  const response = await markCompetitionConfigured(competitionId);
  return unwrapCompetitionDetail(response.data);
}

async function markReady(competitionId: string): Promise<CompetitionDetail> {
  const response = await markCompetitionReady(competitionId);
  return unwrapCompetitionDetail(response.data);
}

async function openCompetitionRegistration(competitionId: string): Promise<CompetitionDetail> {
  const response = await openRegistration(competitionId);
  return unwrapCompetitionDetail(response.data);
}

async function archive(competitionId: string): Promise<CompetitionDetail> {
  const response = await archiveCompetition(competitionId);
  return unwrapCompetitionDetail(response.data);
}

async function createContact(
  competitionId: string,
  payload: AddContact,
): Promise<CompetitionDetail> {
  const response = await addContact(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function deleteContact(competitionId: string, contactId: string): Promise<CompetitionDetail> {
  const response = await removeContact(competitionId, contactId);
  return unwrapCompetitionDetail(response.data);
}

function upsertListItem(
  queryClient: ReturnType<typeof useQueryClient>,
  detail: CompetitionDetail,
): void {
  queryClient.setQueryData<CompetitionSummary[]>(competitionKeys.list(), (current) => {
    const summary = toSummary(detail);
    if (!current) {
      return [summary];
    }
    const index = current.findIndex((item) => item.id === detail.id);
    if (index === -1) {
      return [summary, ...current];
    }
    const next = [...current];
    next[index] = summary;
    return next;
  });
}

/**
 * Writes detail into the cache only when the response is at least as new as the
 * cached copy (by version, then updatedAt). Prevents an in-flight autosave from
 * overwriting a newer backend snapshot.
 */
function setCompetitionCache(
  queryClient: ReturnType<typeof useQueryClient>,
  detail: CompetitionDetail,
): void {
  const key = competitionKeys.detail(detail.id);
  const existing = queryClient.getQueryData<CompetitionDetail>(key);

  if (
    existing &&
    (existing.version > detail.version ||
      (existing.version === detail.version &&
        Date.parse(existing.updatedAt) > Date.parse(detail.updatedAt)))
  ) {
    upsertListItem(queryClient, existing);
    return;
  }

  queryClient.setQueryData(key, detail);
  upsertListItem(queryClient, detail);
}

export function useCompetitionsList(): UseQueryResult<CompetitionSummary[], ApiError> {
  return useQuery<CompetitionSummary[], ApiError>({
    queryKey: competitionKeys.list(),
    queryFn: ({ signal }) => fetchCompetitions(signal),
  });
}

export function useCompetitionDetail(
  competitionId: string | undefined,
): UseQueryResult<CompetitionDetail, ApiError> {
  return useQuery<CompetitionDetail, ApiError>({
    queryKey: competitionKeys.detail(competitionId ?? ""),
    queryFn: ({ signal }) => fetchCompetition(competitionId ?? "", signal),
    enabled: Boolean(competitionId),
  });
}

export function useCreateCompetitionMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  CreateCompetition
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, CreateCompetition>({
    mutationFn: createDraftCompetition,
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUpdateGeneralInformationMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: PatchedUpdateCompetitionGeneralInformation }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: PatchedUpdateCompetitionGeneralInformation }
  >({
    mutationFn: ({ competitionId, payload }) => patchGeneralInformation(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUpdateBrandingMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: PatchedUpdateCompetitionBranding }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: PatchedUpdateCompetitionBranding }
  >({
    mutationFn: ({ competitionId, payload }) => patchBranding(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUploadPosterMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; file: File }
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, { competitionId: string; file: File }>({
    mutationFn: ({ competitionId, file }) => uploadPoster(competitionId, file),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUploadRegulationFileMutation(): UseMutationResult<
  string,
  ApiError,
  { competitionId: string; file: File }
> {
  return useMutation<string, ApiError, { competitionId: string; file: File }>({
    mutationFn: ({ competitionId, file }) => uploadRegulationPdf(competitionId, file),
  });
}

export function useAddRegulationMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: AddRegulation }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: AddRegulation }
  >({
    mutationFn: ({ competitionId, payload }) => publishRegulation(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useMakeRegulationCurrentMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; regulationId: string }
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, { competitionId: string; regulationId: string }>({
    mutationFn: ({ competitionId, regulationId }) =>
      setCurrentRegulation(competitionId, regulationId),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useRemoveRegulationMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; regulationId: string }
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, { competitionId: string; regulationId: string }>({
    mutationFn: ({ competitionId, regulationId }) => deleteRegulation(competitionId, regulationId),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useMarkConfiguredMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  string
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, string>({
    mutationFn: markConfigured,
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useMarkReadyMutation(): UseMutationResult<CompetitionDetail, ApiError, string> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, string>({
    mutationFn: markReady,
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function usePublishCompetitionMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  string
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, string>({
    mutationFn: publish,
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useOpenRegistrationMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  string
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, string>({
    mutationFn: openCompetitionRegistration,
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useArchiveCompetitionMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  string,
  {
    previousList: CompetitionSummary[] | undefined;
    previousDetail: CompetitionDetail | undefined;
  }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    string,
    {
      previousList: CompetitionSummary[] | undefined;
      previousDetail: CompetitionDetail | undefined;
    }
  >({
    mutationFn: archive,
    onMutate: async (competitionId) => {
      await queryClient.cancelQueries({ queryKey: competitionKeys.list() });
      await queryClient.cancelQueries({ queryKey: competitionKeys.detail(competitionId) });

      const previousList = queryClient.getQueryData<CompetitionSummary[]>(competitionKeys.list());
      const previousDetail = queryClient.getQueryData<CompetitionDetail>(
        competitionKeys.detail(competitionId),
      );

      if (previousList) {
        queryClient.setQueryData<CompetitionSummary[]>(
          competitionKeys.list(),
          previousList.map((item) =>
            item.id === competitionId ? { ...item, status: "ARCHIVED" } : item,
          ),
        );
      }

      if (previousDetail) {
        queryClient.setQueryData<CompetitionDetail>(competitionKeys.detail(competitionId), {
          ...previousDetail,
          status: "ARCHIVED",
        });
      }

      return { previousList, previousDetail };
    },
    onError: (_error, competitionId, context) => {
      if (context?.previousList) {
        queryClient.setQueryData(competitionKeys.list(), context.previousList);
      }
      if (context?.previousDetail) {
        queryClient.setQueryData(competitionKeys.detail(competitionId), context.previousDetail);
      }
    },
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useSyncContactMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  {
    competitionId: string;
    contactType: string;
    value: string;
    existingContactId?: string;
  }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    {
      competitionId: string;
      contactType: string;
      value: string;
      existingContactId?: string;
    }
  >({
    mutationFn: async ({ competitionId, contactType, value, existingContactId }) => {
      if (existingContactId) {
        await deleteContact(competitionId, existingContactId);
      }
      if (value.trim().length === 0) {
        return fetchCompetition(competitionId);
      }
      return createContact(competitionId, {
        contactType,
        value: value.trim(),
        isPrimary: false,
      });
    },
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUploadDocumentFileMutation(): UseMutationResult<
  string,
  ApiError,
  { competitionId: string; file: File }
> {
  return useMutation<string, ApiError, { competitionId: string; file: File }>({
    mutationFn: ({ competitionId, file }) => uploadDocumentFile(competitionId, file),
  });
}

export function useAddDocumentMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: AddDocument }
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, { competitionId: string; payload: AddDocument }>({
    mutationFn: ({ competitionId, payload }) => createDocument(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUpdateDocumentMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; documentId: string; payload: PatchedUpdateDocument }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; documentId: string; payload: PatchedUpdateDocument }
  >({
    mutationFn: ({ competitionId, documentId, payload }) =>
      patchDocument(competitionId, documentId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useRemoveDocumentMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; documentId: string }
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, { competitionId: string; documentId: string }>({
    mutationFn: ({ competitionId, documentId }) => deleteDocument(competitionId, documentId),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useSetDocumentPublishedMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; documentId: string; published: boolean }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; documentId: string; published: boolean }
  >({
    mutationFn: ({ competitionId, documentId, published }) =>
      setDocumentPublished(competitionId, documentId, published),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useReorderDocumentsMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  {
    competitionId: string;
    updates: Array<{ documentId: string; payload: PatchedUpdateDocument }>;
  }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    {
      competitionId: string;
      updates: Array<{ documentId: string; payload: PatchedUpdateDocument }>;
    }
  >({
    mutationFn: async ({ competitionId, updates }) => {
      let latest: CompetitionDetail | null = null;
      for (const update of updates) {
        latest = await patchDocument(competitionId, update.documentId, update.payload);
      }
      if (!latest) {
        return fetchCompetition(competitionId);
      }
      return latest;
    },
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}
