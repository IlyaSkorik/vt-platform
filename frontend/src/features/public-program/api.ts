/**
 * Data access for a published programme screen (anyone-facing).
 *
 * Deliberately separate from `program-builder`: this reads one unauthenticated
 * endpoint by slug and knows nothing about programme ids, items or editing. Kept apart
 * so an organizer-only field can never drift into the public screen.
 */
import { type UseQueryResult, useQuery } from "@tanstack/react-query";

import { type ApiError, apiClient, toApiError } from "@/shared/api";

/** One line of a public programme. */
export interface PublicProgramItem {
  position: number;
  kind: string;
  title: string;
  performer: string | null;
  teachers: string[];
  organization: string | null;
  durationSeconds: number;
  startsAt: string | null;
  /** The applicant's note about the act — what the engineer and the host need. */
  note: string | null;
}

/** What a public link resolves to. */
export interface PublicProgram {
  name: string;
  slug: string;
  competitionTitle: string | null;
  nomination: string | null;
  startsAt: string | null;
  totalSeconds: number;
  items: PublicProgramItem[];
}

export const publicProgramKeys = {
  detail: (slug: string) => ["public-program", slug] as const,
};

export async function fetchPublicProgram(
  slug: string,
  signal?: AbortSignal,
): Promise<PublicProgram> {
  try {
    const body = await apiClient(`public/programs/${encodeURIComponent(slug)}`, {
      ...(signal ? { signal } : {}),
    }).json<{ data: PublicProgram }>();
    return body.data;
  } catch (error) {
    throw await toApiError(error);
  }
}

export function usePublicProgram(
  slug: string | undefined,
): UseQueryResult<PublicProgram, ApiError> {
  return useQuery<PublicProgram, ApiError>({
    enabled: Boolean(slug),
    queryKey: publicProgramKeys.detail(slug ?? ""),
    queryFn: ({ signal }) => fetchPublicProgram(slug ?? "", signal),
    // A screen by the stage is left open all day: keep it reasonably fresh without
    // turning this into live tracking (which is a later step).
    refetchInterval: 60_000,
    retry: false,
  });
}
