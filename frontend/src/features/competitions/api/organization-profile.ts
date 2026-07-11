import { type UseQueryResult, useQuery } from "@tanstack/react-query";
import { type ApiError, apiClient, toApiError } from "@/shared/api";

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
}

export const organizationKeys = {
  profile: ["organization", "profile"] as const,
};

interface OrganizationProfileEnvelope {
  data: OrganizationProfile;
  meta?: { requestId?: string };
}

export async function fetchOrganizationProfile(): Promise<OrganizationProfile> {
  try {
    const response = await apiClient.get("organization/profile");
    const body = (await response.json()) as OrganizationProfileEnvelope;
    return body.data;
  } catch (error) {
    throw await toApiError(error);
  }
}

export function useOrganizationProfileQuery(): UseQueryResult<OrganizationProfile, ApiError> {
  return useQuery<OrganizationProfile, ApiError>({
    queryKey: organizationKeys.profile,
    queryFn: fetchOrganizationProfile,
    staleTime: 60_000,
  });
}
