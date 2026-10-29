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
 *
 * The cost of that cadence is carried by HTTP, not by cleverness here: the endpoint sends
 * an `ETag`, the browser revalidates with `If-None-Match` on its own, and a poll that finds
 * nothing changed - which is nearly all of them - costs a bodyless `304`. Nothing in this
 * file has to know that; it is the reason a five-second poll stays cheap with a hall full
 * of phones on it.
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
  /**
   * Whether this column is about somebody who is not on stage — a teacher's phone, a
   * comment that carries «аллергия», «опекун». Advice from the backend rather than a
   * gate: the cells arrive either way, and it is the host's screen that keeps them
   * covered until she asks for one.
   */
  sensitive: boolean;
}

/**
 * How far one row has got on the day.
 *
 * `CANCELLED` is not a stronger `SKIPPED`: skipped is an act the host stepped over and
 * may come back to, cancelled is one that is not happening today — ill, stuck on the
 * road — and every screen reading the programme needs to be told which it was.
 */
export type PublicProgramProgress = "PENDING" | "ON_STAGE" | "PERFORMED" | "SKIPPED" | "CANCELLED";

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
  /**
   * The host's own two marks, and `null` on every other edition — not hidden by this
   * client, absent from the payload. Who is standing behind the stage and what the host
   * wrote to herself about an act are not facts the festival publishes.
   */
  backstage: boolean | null;
  note: string | null;
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
    refetchInterval: (query) => livePollInterval(query.state.data, isHidden()),
    refetchIntervalInBackground: true,
    // Both of these exist to restart a poll this file deliberately stops.
    //
    // A viewer who switches away stops polling (see `livePollInterval`), and nothing
    // starts it again on its own: the interval is recomputed only when a fetch settles,
    // so a screen that stopped while hidden stays stopped after it comes back — for the
    // rest of the festival, showing a running order frozen at the moment of the switch.
    // Coming back to the tab is the event that restarts it, which is what
    // `refetchOnWindowFocus` subscribes to (the platform default turns it off).
    //
    // `staleTime: 0` is what makes that refetch actually happen: a refetch on focus is
    // skipped while the data is still fresh, and the platform's 30s freshness window is
    // six polls of a programme that changes while people watch. Both halves are needed —
    // with the default window, a viewer back inside 30 seconds would get no refetch, and
    // so no new interval either.
    refetchOnWindowFocus: true,
    staleTime: 0,
    retry: false,
  });
}

/**
 * How long until this screen should re-read the programme, or `false` to stop for now.
 *
 * Visible, everyone polls. Hidden, only the edition that drives the day keeps polling: a
 * phone in a pocket and a switched-away tab show nobody anything, and on return the
 * refetch on focus — switched on in `usePublicProgram`, since the platform default is
 * off — both shows that viewer a current programme and starts the interval again. A display beside the stage is the opposite case: nothing ever brings
 * it back to the foreground, and it has to be right whenever somebody glances at it.
 *
 * An edition whose first read has not landed yet keeps polling: it may turn out to be the
 * host's, and one wasted request beats a screen that never starts.
 */
export function livePollInterval(
  program: PublicProgram | undefined,
  hidden: boolean,
): number | false {
  if (!hidden || program === undefined) {
    return LIVE_REFETCH_MS;
  }
  return program.controlsRunningOrder ? LIVE_REFETCH_MS : false;
}

/** Whether the page is currently out of sight. Guarded so it is safe under SSR and jsdom. */
function isHidden(): boolean {
  return typeof document !== "undefined" && document.visibilityState === "hidden";
}

/**
 * Shared plumbing for every write the host's link makes.
 *
 * All of them answer with the whole programme, which is written straight into the cache:
 * the host's own screen is then exact immediately, without waiting for the next poll.
 */
function useHostMutation<TVariables>(
  slug: string,
  send: (variables: TVariables) => Promise<{ data: PublicProgram }>,
): UseMutationResult<PublicProgram, ApiError, TVariables> {
  const queryClient = useQueryClient();
  return useMutation<PublicProgram, ApiError, TVariables>({
    // A poll that was already on its way carries the table as it was *before* this
    // write, and it lands after the answer to the write does — so the host's own screen
    // jumps back to what they just changed and stays wrong until the next tick. In front
    // of a hall that reads as the button not having worked, and the second press puts the
    // act that is already on stage back on it.
    //
    // So the poll in flight is cancelled before the write goes out: there is nothing left
    // to overwrite the answer with, and the next tick asks again a few seconds later.
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: publicProgramKeys.detail(slug) });
    },
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

/** Mark one act as present behind the stage, or no longer present. Host's link only. */
export function useSetRowBackstage(
  slug: string,
): UseMutationResult<PublicProgram, ApiError, { itemId: string; backstage: boolean }> {
  return useHostMutation(slug, ({ itemId, backstage }) =>
    apiClient(`public/programs/${encodeURIComponent(slug)}/rows/${itemId}/backstage`, {
      method: "put",
      // The whole answer rather than "toggle": the host may have this link open on two
      // screens, and an inversion sent from both lands wherever the second one found it.
      json: { backstage },
    }).json<{ data: PublicProgram }>(),
  );
}

/** Write the host's own note against one row (blank clears it). Host's link only. */
export function useSetRowNote(
  slug: string,
): UseMutationResult<PublicProgram, ApiError, { itemId: string; note: string }> {
  return useHostMutation(slug, ({ itemId, note }) =>
    apiClient(`public/programs/${encodeURIComponent(slug)}/rows/${itemId}/note`, {
      method: "put",
      json: { note },
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
