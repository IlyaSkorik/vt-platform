/**
 * Data access for a published programme screen (anyone-facing), including the host's.
 *
 * Deliberately separate from `program-builder`: this reads one unauthenticated endpoint by
 * slug and knows nothing about programme ids, items or editing. Kept apart so an
 * organizer-only field can never drift into the public screen.
 *
 * "Real time" here is a short poll, not a push: every screen refetches on a few-second
 * cadence, and the host's writes answer with the whole programme so their own view is
 * exact immediately. That needs no new transport, and a server-sent-events stream is the
 * natural upgrade when the polling cost stops being negligible.
 */
import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { type ApiError, apiClient, toApiError } from "@/shared/api";

/** One published column: its stable key and the header it is printed under. */
export interface PublicProgramColumn {
  key: string;
  label: string;
  custom: boolean;
}

/** How far one row has got on the day. */
export type PublicProgramProgress = "PENDING" | "ON_STAGE" | "PERFORMED" | "SKIPPED";

/**
 * One row of the table. `cells` is aligned with the programme's `columns`.
 *
 * There is no field-by-field shape here on purpose: the backend renders only the
 * published columns into cells, so a column the organizer left out does not exist in
 * this payload at all. `id` is present only on the host's edition.
 */
export interface PublicProgramRow {
  kind: string;
  cells: string[];
  progress: PublicProgramProgress;
  id: string | null;
}

/** What a public link resolves to: a table cut to the columns the organizer chose. */
export interface PublicProgram {
  name: string;
  slug: string;
  competitionTitle: string | null;
  nomination: string | null;
  startsAt: string | null;
  totalSeconds: number;
  /** Whether this link may drive the running order — the host's edition. */
  controlsRunningOrder: boolean;
  columns: PublicProgramColumn[];
  rows: PublicProgramRow[];
}

/**
 * How often a screen re-reads the programme.
 *
 * Short enough that "выступил" reaches a display beside the stage while the applause is
 * still going, long enough to be free at festival scale (a handful of screens per event).
 */
const LIVE_REFETCH_MS = 5_000;

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
    refetchInterval: LIVE_REFETCH_MS,
    // A screen left open all day should keep polling even while the tab is in the
    // background: that is exactly the display beside the stage.
    refetchIntervalInBackground: true,
    retry: false,
  });
}

/**
 * Shared plumbing for the host's two writes.
 *
 * Both answer with the whole programme, which is written straight into the cache: the
 * host's own screen is then exact immediately, without waiting for the next poll.
 */
function useHostMutation<TVariables>(
  slug: string,
  send: (variables: TVariables) => Promise<{ data: PublicProgram }>,
): UseMutationResult<PublicProgram, ApiError, TVariables> {
  const queryClient = useQueryClient();
  return useMutation<PublicProgram, ApiError, TVariables>({
    mutationFn: async (variables) => {
      try {
        return (await send(variables)).data;
      } catch (error) {
        throw await toApiError(error);
      }
    },
    onSuccess: (program) => {
      queryClient.setQueryData(publicProgramKeys.detail(slug), program);
    },
  });
}

/** Mark how far one row has got, from the host's link. */
export function useSetRowProgress(
  slug: string,
): UseMutationResult<PublicProgram, ApiError, { itemId: string; progress: PublicProgramProgress }> {
  return useHostMutation(slug, ({ itemId, progress }) =>
    apiClient(`public/programs/${encodeURIComponent(slug)}/rows/${itemId}/progress`, {
      method: "put",
      json: { progress },
    }).json<{ data: PublicProgram }>(),
  );
}

/** Rearrange what is still to come, from the host's link. */
export function useHostReorder(slug: string): UseMutationResult<PublicProgram, ApiError, string[]> {
  return useHostMutation(slug, (itemIds) =>
    apiClient(`public/programs/${encodeURIComponent(slug)}/order`, {
      method: "put",
      json: { itemIds },
    }).json<{ data: PublicProgram }>(),
  );
}
