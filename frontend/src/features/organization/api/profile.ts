import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { type ApiError, apiClient, toApiError } from "@/shared/api";

/**
 * The entity a festival runs *with the support of*, beside the organizer.
 *
 * A second legal person: by law the entity actually behind an event has to be
 * named, and in practice the organizer of record and the one doing the work are
 * often not the same. Carries its own `legalInformation` for that reason — the
 * organizer's requisites are not its own. Absent as a whole (`null` on the
 * profile) when the organization runs its own festivals, which is the common case.
 */
export interface OrganizationSupporter {
  name: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  address: string | null;
  vk: string | null;
  instagram: string | null;
  telegram: string | null;
  legalInformation: string | null;
}

/**
 * The supporting entity as the PATCH body carries it.
 *
 * `name` is a plain `string` rather than nullable: the form always submits the
 * block, and a blank name is how it says "there is no supporting entity" — the
 * backend drops the whole block on exactly that.
 */
export interface OrganizationSupporterUpdate {
  name: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  address: string | null;
  vk: string | null;
  instagram: string | null;
  telegram: string | null;
  legalInformation: string | null;
}

/** The organization profile read model returned by the staff API. */
export interface OrganizationProfile {
  id: string;
  name: string;
  slug: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  address: string | null;
  logo: string | null;
  vk: string | null;
  instagram: string | null;
  telegram: string | null;
  legalInformation: string | null;
  supporter: OrganizationSupporter | null;
}

/** The editable fields sent to the PATCH endpoint (display name + contacts). */
export interface OrganizationProfileUpdate {
  name: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  address: string | null;
  vk: string | null;
  instagram: string | null;
  telegram: string | null;
  legalInformation: string | null;
  supporter: OrganizationSupporterUpdate;
}

interface OrganizationProfileEnvelope {
  data: OrganizationProfile;
  meta?: { requestId?: string };
}

export const organizationProfileKeys = {
  profile: ["organization", "profile"] as const,
};

const PROFILE_PATH = "organization/profile";

async function request<T>(path: string, options?: Parameters<typeof apiClient>[1]): Promise<T> {
  try {
    return await apiClient(path, options).json<T>();
  } catch (error) {
    throw await toApiError(error);
  }
}

export async function fetchOrganizationProfile(): Promise<OrganizationProfile> {
  const body = await request<OrganizationProfileEnvelope>(PROFILE_PATH);
  return body.data;
}

export async function updateOrganizationProfile(
  update: OrganizationProfileUpdate,
): Promise<OrganizationProfile> {
  const body = await request<OrganizationProfileEnvelope>(PROFILE_PATH, {
    method: "PATCH",
    json: update,
  });
  return body.data;
}

export function useOrganizationProfileQuery(): UseQueryResult<OrganizationProfile, ApiError> {
  return useQuery<OrganizationProfile, ApiError>({
    queryKey: organizationProfileKeys.profile,
    queryFn: fetchOrganizationProfile,
    staleTime: 60_000,
  });
}

export function useUpdateOrganizationProfileMutation(): UseMutationResult<
  OrganizationProfile,
  ApiError,
  OrganizationProfileUpdate
> {
  const queryClient = useQueryClient();
  return useMutation<OrganizationProfile, ApiError, OrganizationProfileUpdate>({
    mutationFn: updateOrganizationProfile,
    onSuccess: (profile) => {
      queryClient.setQueryData(organizationProfileKeys.profile, profile);
    },
  });
}
