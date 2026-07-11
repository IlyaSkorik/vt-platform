import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { ApiError, apiClient, toApiError } from "@/shared/api";
import {
  addAdditionalService,
  addAdmissionRule,
  addAgeCategory,
  addCategory,
  addContact,
  addDiscipline,
  addDocument,
  addParticipantGroup,
  addParticipationFormat,
  addPricingRule,
  addRegulation,
  archiveCompetition,
  changePrice,
  disableAdditionalService,
  enableAdditionalService,
  getCompetition,
  listCompetitions,
  makeRegulationCurrent,
  markCompetitionConfigured,
  markCompetitionReady,
  openRegistration,
  postCompetition,
  publishCompetition,
  publishDocument,
  removeAdditionalService,
  removeAdmissionRule,
  removeAgeCategory,
  removeCategory,
  removeContact,
  removeDiscipline,
  removeDocument,
  removeParticipantGroup,
  removeParticipationFormat,
  removePricingRule,
  removeRegulation,
  renameCategory,
  renameDiscipline,
  unpublishDocument,
  updateAdditionalService,
  updateAgeCategory,
  updateBranding,
  updateCompetition,
  updateDocument,
  updateParticipantGroup,
  updateParticipationFormat,
  updateSettings,
} from "@/shared/api/generated/competitions/competitions";
import type {
  AddAdditionalService,
  AddAdmissionRule,
  AddAgeCategory,
  AddCategory,
  AddContact,
  AddDiscipline,
  AddDocument,
  AddParticipantGroup,
  AddParticipationFormat,
  AddPricingRule,
  AddRegulation,
  CompetitionDetail,
  CompetitionSummary,
  CreateCompetition,
  PatchedChangePrice,
  PatchedRenameCategory,
  PatchedRenameDiscipline,
  PatchedUpdateAdditionalService,
  PatchedUpdateAgeCategory,
  PatchedUpdateCompetitionBranding,
  PatchedUpdateCompetitionGeneralInformation,
  PatchedUpdateDocument,
  PatchedUpdateParticipantGroup,
  PatchedUpdateParticipationFormat,
  UpdateCompetitionSettings,
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

async function createCategory(
  competitionId: string,
  payload: AddCategory,
): Promise<CompetitionDetail> {
  const response = await addCategory(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function patchCategory(
  competitionId: string,
  categoryId: string,
  payload: PatchedRenameCategory,
): Promise<CompetitionDetail> {
  const response = await renameCategory(competitionId, categoryId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function deleteCategory(
  competitionId: string,
  categoryId: string,
): Promise<CompetitionDetail> {
  const response = await removeCategory(competitionId, categoryId);
  return unwrapCompetitionDetail(response.data);
}

async function createDiscipline(
  competitionId: string,
  payload: AddDiscipline,
): Promise<CompetitionDetail> {
  const response = await addDiscipline(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function patchDiscipline(
  competitionId: string,
  disciplineId: string,
  payload: PatchedRenameDiscipline,
): Promise<CompetitionDetail> {
  const response = await renameDiscipline(competitionId, disciplineId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function deleteDiscipline(
  competitionId: string,
  disciplineId: string,
): Promise<CompetitionDetail> {
  const response = await removeDiscipline(competitionId, disciplineId);
  return unwrapCompetitionDetail(response.data);
}

async function createAgeCategory(
  competitionId: string,
  payload: AddAgeCategory,
): Promise<CompetitionDetail> {
  const response = await addAgeCategory(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function patchAgeCategory(
  competitionId: string,
  ageCategoryId: string,
  payload: PatchedUpdateAgeCategory,
): Promise<CompetitionDetail> {
  const response = await updateAgeCategory(competitionId, ageCategoryId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function deleteAgeCategory(
  competitionId: string,
  ageCategoryId: string,
): Promise<CompetitionDetail> {
  const response = await removeAgeCategory(competitionId, ageCategoryId);
  return unwrapCompetitionDetail(response.data);
}

async function createParticipantGroup(
  competitionId: string,
  payload: AddParticipantGroup,
): Promise<CompetitionDetail> {
  const response = await addParticipantGroup(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function patchParticipantGroup(
  competitionId: string,
  participantGroupId: string,
  payload: PatchedUpdateParticipantGroup,
): Promise<CompetitionDetail> {
  const response = await updateParticipantGroup(competitionId, participantGroupId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function deleteParticipantGroup(
  competitionId: string,
  participantGroupId: string,
): Promise<CompetitionDetail> {
  const response = await removeParticipantGroup(competitionId, participantGroupId);
  return unwrapCompetitionDetail(response.data);
}

async function createParticipationFormat(
  competitionId: string,
  payload: AddParticipationFormat,
): Promise<CompetitionDetail> {
  const response = await addParticipationFormat(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function patchParticipationFormat(
  competitionId: string,
  formatId: string,
  payload: PatchedUpdateParticipationFormat,
): Promise<CompetitionDetail> {
  const response = await updateParticipationFormat(competitionId, formatId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function deleteParticipationFormat(
  competitionId: string,
  formatId: string,
): Promise<CompetitionDetail> {
  const response = await removeParticipationFormat(competitionId, formatId);
  return unwrapCompetitionDetail(response.data);
}

async function createAdmissionRule(
  competitionId: string,
  payload: AddAdmissionRule,
): Promise<CompetitionDetail> {
  const response = await addAdmissionRule(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function deleteAdmissionRule(
  competitionId: string,
  payload: AddAdmissionRule,
): Promise<CompetitionDetail> {
  const response = await removeAdmissionRule(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function createPricingRule(
  competitionId: string,
  payload: AddPricingRule,
): Promise<CompetitionDetail> {
  const response = await addPricingRule(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function patchPrice(
  competitionId: string,
  payload: PatchedChangePrice,
): Promise<CompetitionDetail> {
  const response = await changePrice(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function deletePricingRule(
  competitionId: string,
  payload: {
    categoryId: string;
    disciplineId: string;
    ageCategoryId: string;
    participantGroupId: string;
    participationFormatId: string;
  },
): Promise<CompetitionDetail> {
  const response = await removePricingRule(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function createAdditionalService(
  competitionId: string,
  payload: AddAdditionalService,
): Promise<CompetitionDetail> {
  const response = await addAdditionalService(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function patchAdditionalService(
  competitionId: string,
  serviceId: string,
  payload: PatchedUpdateAdditionalService,
): Promise<CompetitionDetail> {
  const response = await updateAdditionalService(competitionId, serviceId, payload);
  return unwrapCompetitionDetail(response.data);
}

async function deleteAdditionalService(
  competitionId: string,
  serviceId: string,
): Promise<CompetitionDetail> {
  const response = await removeAdditionalService(competitionId, serviceId);
  return unwrapCompetitionDetail(response.data);
}

async function setAdditionalServiceEnabled(
  competitionId: string,
  serviceId: string,
  enabled: boolean,
): Promise<CompetitionDetail> {
  const response = enabled
    ? await enableAdditionalService(competitionId, serviceId)
    : await disableAdditionalService(competitionId, serviceId);
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

export function useAddCategoryMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: AddCategory }
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, { competitionId: string; payload: AddCategory }>({
    mutationFn: ({ competitionId, payload }) => createCategory(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUpdateCategoryMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; categoryId: string; payload: PatchedRenameCategory }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; categoryId: string; payload: PatchedRenameCategory }
  >({
    mutationFn: ({ competitionId, categoryId, payload }) =>
      patchCategory(competitionId, categoryId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useRemoveCategoryMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; categoryId: string }
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, { competitionId: string; categoryId: string }>({
    mutationFn: ({ competitionId, categoryId }) => deleteCategory(competitionId, categoryId),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useReorderCategoriesMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  {
    competitionId: string;
    updates: Array<{ categoryId: string; payload: PatchedRenameCategory }>;
  }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    {
      competitionId: string;
      updates: Array<{ categoryId: string; payload: PatchedRenameCategory }>;
    }
  >({
    mutationFn: async ({ competitionId, updates }) => {
      let latest: CompetitionDetail | null = null;
      for (const update of updates) {
        latest = await patchCategory(competitionId, update.categoryId, update.payload);
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

export function useAddDisciplineMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: AddDiscipline }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: AddDiscipline }
  >({
    mutationFn: ({ competitionId, payload }) => createDiscipline(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUpdateDisciplineMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; disciplineId: string; payload: PatchedRenameDiscipline }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; disciplineId: string; payload: PatchedRenameDiscipline }
  >({
    mutationFn: ({ competitionId, disciplineId, payload }) =>
      patchDiscipline(competitionId, disciplineId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useRemoveDisciplineMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; disciplineId: string }
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, { competitionId: string; disciplineId: string }>({
    mutationFn: ({ competitionId, disciplineId }) => deleteDiscipline(competitionId, disciplineId),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useReorderDisciplinesMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  {
    competitionId: string;
    updates: Array<{ disciplineId: string; payload: PatchedRenameDiscipline }>;
  }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    {
      competitionId: string;
      updates: Array<{ disciplineId: string; payload: PatchedRenameDiscipline }>;
    }
  >({
    mutationFn: async ({ competitionId, updates }) => {
      let latest: CompetitionDetail | null = null;
      for (const update of updates) {
        latest = await patchDiscipline(competitionId, update.disciplineId, update.payload);
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

export function useAddAgeCategoryMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: AddAgeCategory }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: AddAgeCategory }
  >({
    mutationFn: ({ competitionId, payload }) => createAgeCategory(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUpdateAgeCategoryMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; ageCategoryId: string; payload: PatchedUpdateAgeCategory }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; ageCategoryId: string; payload: PatchedUpdateAgeCategory }
  >({
    mutationFn: ({ competitionId, ageCategoryId, payload }) =>
      patchAgeCategory(competitionId, ageCategoryId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useRemoveAgeCategoryMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; ageCategoryId: string }
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, { competitionId: string; ageCategoryId: string }>(
    {
      mutationFn: ({ competitionId, ageCategoryId }) =>
        deleteAgeCategory(competitionId, ageCategoryId),
      onSuccess: (detail) => {
        setCompetitionCache(queryClient, detail);
      },
    },
  );
}

export function useReorderAgeCategoriesMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  {
    competitionId: string;
    updates: Array<{ ageCategoryId: string; payload: PatchedUpdateAgeCategory }>;
  }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    {
      competitionId: string;
      updates: Array<{ ageCategoryId: string; payload: PatchedUpdateAgeCategory }>;
    }
  >({
    mutationFn: async ({ competitionId, updates }) => {
      let latest: CompetitionDetail | null = null;
      for (const update of updates) {
        latest = await patchAgeCategory(competitionId, update.ageCategoryId, update.payload);
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

export function useAddParticipantGroupMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: AddParticipantGroup }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: AddParticipantGroup }
  >({
    mutationFn: ({ competitionId, payload }) => createParticipantGroup(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUpdateParticipantGroupMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  {
    competitionId: string;
    participantGroupId: string;
    payload: PatchedUpdateParticipantGroup;
  }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    {
      competitionId: string;
      participantGroupId: string;
      payload: PatchedUpdateParticipantGroup;
    }
  >({
    mutationFn: ({ competitionId, participantGroupId, payload }) =>
      patchParticipantGroup(competitionId, participantGroupId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useRemoveParticipantGroupMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; participantGroupId: string }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; participantGroupId: string }
  >({
    mutationFn: ({ competitionId, participantGroupId }) =>
      deleteParticipantGroup(competitionId, participantGroupId),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useReorderParticipantGroupsMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  {
    competitionId: string;
    updates: Array<{ participantGroupId: string; payload: PatchedUpdateParticipantGroup }>;
  }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    {
      competitionId: string;
      updates: Array<{ participantGroupId: string; payload: PatchedUpdateParticipantGroup }>;
    }
  >({
    mutationFn: async ({ competitionId, updates }) => {
      let latest: CompetitionDetail | null = null;
      for (const update of updates) {
        latest = await patchParticipantGroup(
          competitionId,
          update.participantGroupId,
          update.payload,
        );
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

export function useAddParticipationFormatMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: AddParticipationFormat }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: AddParticipationFormat }
  >({
    mutationFn: ({ competitionId, payload }) => createParticipationFormat(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUpdateParticipationFormatMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; formatId: string; payload: PatchedUpdateParticipationFormat }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; formatId: string; payload: PatchedUpdateParticipationFormat }
  >({
    mutationFn: ({ competitionId, formatId, payload }) =>
      patchParticipationFormat(competitionId, formatId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useRemoveParticipationFormatMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; formatId: string }
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, { competitionId: string; formatId: string }>({
    mutationFn: ({ competitionId, formatId }) => deleteParticipationFormat(competitionId, formatId),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useReorderParticipationFormatsMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  {
    competitionId: string;
    updates: Array<{ formatId: string; payload: PatchedUpdateParticipationFormat }>;
  }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    {
      competitionId: string;
      updates: Array<{ formatId: string; payload: PatchedUpdateParticipationFormat }>;
    }
  >({
    mutationFn: async ({ competitionId, updates }) => {
      let latest: CompetitionDetail | null = null;
      for (const update of updates) {
        latest = await patchParticipationFormat(competitionId, update.formatId, update.payload);
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

export function useAddAdmissionRuleMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: AddAdmissionRule }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: AddAdmissionRule }
  >({
    mutationFn: ({ competitionId, payload }) => createAdmissionRule(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useRemoveAdmissionRuleMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: AddAdmissionRule }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: AddAdmissionRule }
  >({
    mutationFn: ({ competitionId, payload }) => deleteAdmissionRule(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export interface BulkAdmissionRulesResult {
  detail: CompetitionDetail;
  created: number;
  skipped: number;
}

export function useBulkAddAdmissionRulesMutation(): UseMutationResult<
  BulkAdmissionRulesResult,
  ApiError,
  { competitionId: string; payloads: AddAdmissionRule[]; skippedExisting?: number }
> {
  const queryClient = useQueryClient();
  return useMutation<
    BulkAdmissionRulesResult,
    ApiError,
    { competitionId: string; payloads: AddAdmissionRule[]; skippedExisting?: number }
  >({
    mutationFn: async ({ competitionId, payloads, skippedExisting = 0 }) => {
      let latest: CompetitionDetail | null = null;
      let created = 0;
      let skipped = skippedExisting;

      for (const payload of payloads) {
        try {
          latest = await createAdmissionRule(competitionId, payload);
          created += 1;
        } catch (error) {
          // Duplicate combinations may race; treat conflict as skipped.
          if (error instanceof ApiError && error.isConflict) {
            skipped += 1;
            continue;
          }
          throw error;
        }
      }

      if (!latest) {
        latest = await fetchCompetition(competitionId);
      }

      return {
        detail: latest,
        created,
        skipped,
      };
    },
    onSuccess: (result) => {
      setCompetitionCache(queryClient, result.detail);
    },
  });
}

export type PricingUpsertPayload = AddPricingRule & { mode: "add" | "change" };

export interface BulkPricingResult {
  detail: CompetitionDetail;
  updated: number;
  removed: number;
  failed: number;
}

async function upsertPricingRule(
  competitionId: string,
  payload: PricingUpsertPayload,
): Promise<CompetitionDetail> {
  const body: AddPricingRule = {
    categoryId: payload.categoryId,
    disciplineId: payload.disciplineId,
    ageCategoryId: payload.ageCategoryId,
    participantGroupId: payload.participantGroupId,
    participationFormatId: payload.participationFormatId,
    amount: payload.amount,
  };
  if (payload.currency) {
    body.currency = payload.currency;
  }
  if (payload.calculationType) {
    body.calculationType = payload.calculationType;
  }
  if (payload.mode === "change") {
    return patchPrice(competitionId, body);
  }
  return createPricingRule(competitionId, body);
}

export function useUpsertPricingRuleMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: PricingUpsertPayload },
  { previous?: CompetitionDetail }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: PricingUpsertPayload },
    { previous?: CompetitionDetail }
  >({
    mutationFn: ({ competitionId, payload }) => upsertPricingRule(competitionId, payload),
    onMutate: async ({ competitionId, payload }) => {
      await queryClient.cancelQueries({ queryKey: competitionKeys.detail(competitionId) });
      const previous = queryClient.getQueryData<CompetitionDetail>(
        competitionKeys.detail(competitionId),
      );
      if (previous) {
        const key = [
          payload.categoryId,
          payload.disciplineId,
          payload.ageCategoryId,
          payload.participantGroupId,
          payload.participationFormatId,
        ].join("|");
        const nextRules = previous.pricingRules.filter(
          (rule) =>
            [
              rule.categoryId,
              rule.disciplineId,
              rule.ageCategoryId,
              rule.participantGroupId,
              rule.participationFormatId,
            ].join("|") !== key,
        );
        nextRules.push({
          categoryId: payload.categoryId,
          disciplineId: payload.disciplineId,
          ageCategoryId: payload.ageCategoryId,
          participantGroupId: payload.participantGroupId,
          participationFormatId: payload.participationFormatId,
          amount: payload.amount,
          currency: payload.currency ?? "BYN",
          calculationType: payload.calculationType ?? "PER_PARTICIPANT",
        });
        queryClient.setQueryData(competitionKeys.detail(competitionId), {
          ...previous,
          pricingRules: nextRules,
        });
        return { previous };
      }
      return {};
    },
    onError: (_error, variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(competitionKeys.detail(variables.competitionId), context.previous);
      }
    },
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useRemovePricingRuleMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  {
    competitionId: string;
    payload: {
      categoryId: string;
      disciplineId: string;
      ageCategoryId: string;
      participantGroupId: string;
      participationFormatId: string;
    };
  },
  { previous?: CompetitionDetail }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    {
      competitionId: string;
      payload: {
        categoryId: string;
        disciplineId: string;
        ageCategoryId: string;
        participantGroupId: string;
        participationFormatId: string;
      };
    },
    { previous?: CompetitionDetail }
  >({
    mutationFn: ({ competitionId, payload }) => deletePricingRule(competitionId, payload),
    onMutate: async ({ competitionId, payload }) => {
      await queryClient.cancelQueries({ queryKey: competitionKeys.detail(competitionId) });
      const previous = queryClient.getQueryData<CompetitionDetail>(
        competitionKeys.detail(competitionId),
      );
      if (previous) {
        const key = [
          payload.categoryId,
          payload.disciplineId,
          payload.ageCategoryId,
          payload.participantGroupId,
          payload.participationFormatId,
        ].join("|");
        queryClient.setQueryData(competitionKeys.detail(competitionId), {
          ...previous,
          pricingRules: previous.pricingRules.filter(
            (rule) =>
              [
                rule.categoryId,
                rule.disciplineId,
                rule.ageCategoryId,
                rule.participantGroupId,
                rule.participationFormatId,
              ].join("|") !== key,
          ),
        });
        return { previous };
      }
      return {};
    },
    onError: (_error, variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(competitionKeys.detail(variables.competitionId), context.previous);
      }
    },
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useBulkPricingMutation(): UseMutationResult<
  BulkPricingResult,
  ApiError,
  {
    competitionId: string;
    upserts: PricingUpsertPayload[];
    removes: Array<{
      categoryId: string;
      disciplineId: string;
      ageCategoryId: string;
      participantGroupId: string;
      participationFormatId: string;
    }>;
  }
> {
  const queryClient = useQueryClient();
  return useMutation<
    BulkPricingResult,
    ApiError,
    {
      competitionId: string;
      upserts: PricingUpsertPayload[];
      removes: Array<{
        categoryId: string;
        disciplineId: string;
        ageCategoryId: string;
        participantGroupId: string;
        participationFormatId: string;
      }>;
    }
  >({
    mutationFn: async ({ competitionId, upserts, removes }) => {
      let latest: CompetitionDetail | null = null;
      let updated = 0;
      let removed = 0;
      let failed = 0;

      for (const payload of upserts) {
        try {
          latest = await upsertPricingRule(competitionId, payload);
          updated += 1;
        } catch {
          failed += 1;
        }
      }

      for (const payload of removes) {
        try {
          latest = await deletePricingRule(competitionId, payload);
          removed += 1;
        } catch {
          failed += 1;
        }
      }

      if (!latest) {
        latest = await fetchCompetition(competitionId);
      }

      return { detail: latest, updated, removed, failed };
    },
    onSuccess: (result) => {
      setCompetitionCache(queryClient, result.detail);
    },
  });
}

export function useAddAdditionalServiceMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: AddAdditionalService }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: AddAdditionalService }
  >({
    mutationFn: ({ competitionId, payload }) => createAdditionalService(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useUpdateAdditionalServiceMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; serviceId: string; payload: PatchedUpdateAdditionalService }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; serviceId: string; payload: PatchedUpdateAdditionalService }
  >({
    mutationFn: ({ competitionId, serviceId, payload }) =>
      patchAdditionalService(competitionId, serviceId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useRemoveAdditionalServiceMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; serviceId: string }
> {
  const queryClient = useQueryClient();
  return useMutation<CompetitionDetail, ApiError, { competitionId: string; serviceId: string }>({
    mutationFn: ({ competitionId, serviceId }) => deleteAdditionalService(competitionId, serviceId),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useSetAdditionalServiceEnabledMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; serviceId: string; enabled: boolean }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; serviceId: string; enabled: boolean }
  >({
    mutationFn: ({ competitionId, serviceId, enabled }) =>
      setAdditionalServiceEnabled(competitionId, serviceId, enabled),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

async function putSettings(
  competitionId: string,
  payload: UpdateCompetitionSettings,
): Promise<CompetitionDetail> {
  const response = await updateSettings(competitionId, payload);
  return unwrapCompetitionDetail(response.data);
}

export function useUpdateCompetitionSettingsMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  { competitionId: string; payload: UpdateCompetitionSettings }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    { competitionId: string; payload: UpdateCompetitionSettings }
  >({
    mutationFn: ({ competitionId, payload }) => putSettings(competitionId, payload),
    onSuccess: (detail) => {
      setCompetitionCache(queryClient, detail);
    },
  });
}

export function useReorderAdditionalServicesMutation(): UseMutationResult<
  CompetitionDetail,
  ApiError,
  {
    competitionId: string;
    updates: Array<{ serviceId: string; payload: PatchedUpdateAdditionalService }>;
  }
> {
  const queryClient = useQueryClient();
  return useMutation<
    CompetitionDetail,
    ApiError,
    {
      competitionId: string;
      updates: Array<{ serviceId: string; payload: PatchedUpdateAdditionalService }>;
    }
  >({
    mutationFn: async ({ competitionId, updates }) => {
      let latest: CompetitionDetail | null = null;
      for (const update of updates) {
        latest = await patchAdditionalService(competitionId, update.serviceId, update.payload);
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
