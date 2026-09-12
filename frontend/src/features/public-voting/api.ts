/**
 * Data access for the audience's voting page (anyone-facing).
 *
 * Deliberately separate from `voting-builder`: this reads one unauthenticated
 * endpoint by slug and knows nothing about ballot ids, nominee editing or the
 * organizer's settings. Kept apart so an organizer-only field can never drift
 * onto a page the whole hall is looking at.
 *
 * The vote answers with the *whole* page state, which is written straight into the
 * cache. That is what makes the screen exact the instant somebody taps — no second
 * request, no gap where the button has been pressed but nothing has changed.
 *
 * Cookies ride along on their own: `apiClient` sends credentials, and the voter
 * token the server sets is httpOnly, so nothing here ever touches it.
 */
import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { type ApiError, apiClient, toApiError } from "@/shared/api";

/** One entry the audience may vote for. */
export interface PublicNominee {
  id: string;
  position: number;
  title: string;
  subtitle: string;
  photo: string | null;
  number: number | null;
  /**
   * The running count, or `null` when this ballot does not show it yet.
   *
   * Absent rather than zero on purpose: a page must not render "0 голосов" for
   * something it merely is not allowed to know.
   */
  votes: number | null;
  /** Whether this reader has already backed this nominee in the current window. */
  chosen: boolean;
}

export type PublicBallotStatus = "DRAFT" | "OPEN" | "CLOSED";

/** What a voting link resolves to. */
export interface PublicBallot {
  title: string;
  description: string;
  slug: string;
  status: PublicBallotStatus;
  /** Whether a vote sent right now would be counted (the window included). */
  open: boolean;
  votesPerVoter: number;
  /** How many of their votes this reader still has in the current window. */
  votesLeft: number;
  revealTotals: boolean;
  nominees: PublicNominee[];
  totalVotes: number | null;
  closesAt: string | null;
  /** Why voting is not possible, written for the person holding the phone. */
  closedReason: string | null;
}

export interface VoteReceipt {
  ballot: PublicBallot;
  accepted: string[];
}

/**
 * How often a screen re-reads the ballot.
 *
 * Short, because the number on a scoreboard beside a stage is the whole point of
 * the screen and one that sits still for a minute reads as broken. Cheap at
 * festival scale: a handful of screens per event, and a voter's own phone stops
 * polling the moment it goes into a pocket (see below).
 */
const LIVE_REFETCH_MS = 5_000;

export const publicBallotKeys = {
  detail: (slug: string) => ["public-ballot", slug] as const,
};

export async function fetchPublicBallot(slug: string, signal?: AbortSignal): Promise<PublicBallot> {
  try {
    const body = await apiClient(`public/ballots/${encodeURIComponent(slug)}`, {
      ...(signal ? { signal } : {}),
    }).json<{ data: PublicBallot }>();
    return body.data;
  } catch (error) {
    throw await toApiError(error);
  }
}

/**
 * The voting page.
 *
 * `live` is for the board beside the stage: it keeps polling while out of sight,
 * because nothing ever brings a projector back to the foreground and it has to be
 * right whenever somebody glances at it. A voter's phone does not — a screen in a
 * pocket shows nobody anything, and TanStack refetches on focus, so they see a
 * current page the moment they look.
 */
export function usePublicBallot(
  slug: string | undefined,
  { live = false }: { live?: boolean } = {},
): UseQueryResult<PublicBallot, ApiError> {
  return useQuery<PublicBallot, ApiError>({
    enabled: Boolean(slug),
    queryKey: publicBallotKeys.detail(slug ?? ""),
    queryFn: ({ signal }) => fetchPublicBallot(slug ?? "", signal),
    refetchInterval: () => (live || !isHidden() ? LIVE_REFETCH_MS : false),
    refetchIntervalInBackground: live,
    retry: false,
  });
}

/**
 * Cast a vote.
 *
 * Several ids in one request, so a ballot allowing more than one pick accepts or
 * refuses the whole submission at once — nobody is left with two of their three
 * votes spent and an error on screen.
 */
export function useCastVote(slug: string): UseMutationResult<VoteReceipt, ApiError, string[]> {
  const queryClient = useQueryClient();
  return useMutation<VoteReceipt, ApiError, string[]>({
    mutationFn: async (nomineeIds) => {
      try {
        const body = await apiClient(`public/ballots/${encodeURIComponent(slug)}/votes`, {
          method: "post",
          json: { nomineeIds },
        }).json<{ data: VoteReceipt }>();
        return body.data;
      } catch (error) {
        throw await toApiError(error);
      }
    },
    onSuccess: (receipt) => {
      queryClient.setQueryData(publicBallotKeys.detail(slug), receipt.ballot);
    },
    // A refusal is usually "you already voted" or "the vote just closed", and both
    // are facts about the page rather than about the request: re-read it so the
    // screen agrees with the server instead of arguing with it.
    onError: () => {
      void queryClient.invalidateQueries({ queryKey: publicBallotKeys.detail(slug) });
    },
  });
}

/** Whether the page is out of sight. Guarded so it is safe under SSR and jsdom. */
function isHidden(): boolean {
  return typeof document !== "undefined" && document.visibilityState === "hidden";
}
