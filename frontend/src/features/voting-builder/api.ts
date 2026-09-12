/**
 * Data access for the organizer's ballots.
 *
 * Deliberately separate from `public-voting`: this one speaks in ballot ids and
 * carries the counts, the settings and the withdrawn nominees. Keeping the two
 * apart is what stops an organizer-only field from drifting onto a page the whole
 * hall can read.
 *
 * Every write answers with the whole recomputed ballot, which is written straight
 * into the cache — adding a nominee renumbers the rest, so a client that renders
 * the response is never showing a stale list.
 */
import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { type ApiError, apiClient, toApiError } from "@/shared/api";

export type BallotStatus = "DRAFT" | "OPEN" | "CLOSED";

/** Who may see the running count, and when. */
export type RevealPolicy = "ALWAYS" | "AFTER_CLOSE" | "NEVER";

export interface Nominee {
  id: string;
  position: number;
  title: string;
  subtitle: string;
  photo: string | null;
  number: number | null;
  /** Off the ballot but still in the results, with the votes they had. */
  withdrawn: boolean;
  votes: number;
  submissionId: string | null;
  programItemId: string | null;
}

export interface BallotSummary {
  id: string;
  title: string;
  slug: string;
  status: BallotStatus;
  competitionId: string | null;
  /** Whether this ballot runs without a festival on the platform. */
  standalone: boolean;
  nominees: number;
  totalVotes: number;
  opensAt: string | null;
  closesAt: string | null;
  createdAt: string;
}

export interface Ballot extends Omit<BallotSummary, "nominees"> {
  description: string;
  votesPerVoter: number;
  cooldownHours: number;
  reveal: RevealPolicy;
  nominees: Nominee[];
  /** Distinct people, not votes — the two differ on a multi-vote ballot. */
  voters: number;
  updatedAt: string | null;
}

/** One running order a ballot could be filled from, and how much is in it. */
export interface ProgramOption {
  id: string;
  name: string;
  nominees: number;
}

export interface ImportError {
  /** The row number as Excel shows it — the one the organizer will look for. */
  row: number;
  message: string;
}

export interface ImportPreview {
  added: Nominee[];
  errors: ImportError[];
  /** Columns we read that this file did not have. */
  missingColumns: string[];
  dryRun: boolean;
}

export interface CreateBallotInput {
  title: string;
  competitionId?: string | null;
  description?: string;
  opensAt?: string | null;
  closesAt?: string | null;
  votesPerVoter?: number;
  cooldownHours?: number;
  reveal?: RevealPolicy;
}

export type UpdateBallotInput = Partial<CreateBallotInput>;

export interface NomineeInput {
  title: string;
  subtitle?: string;
  number?: number | null;
}

export const ballotKeys = {
  all: ["ballots"] as const,
  list: (competitionId: string | null) => ["ballots", "list", competitionId ?? "all"] as const,
  detail: (ballotId: string) => ["ballots", "detail", ballotId] as const,
  programs: (ballotId: string) => ["ballots", "programs", ballotId] as const,
};

async function unwrap<T>(promise: Promise<{ data: T }>): Promise<T> {
  try {
    return (await promise).data;
  } catch (error) {
    throw await toApiError(error);
  }
}

export function useBallots(
  competitionId: string | null = null,
): UseQueryResult<BallotSummary[], ApiError> {
  return useQuery<BallotSummary[], ApiError>({
    queryKey: ballotKeys.list(competitionId),
    queryFn: ({ signal }) => {
      const query = competitionId ? `?competitionId=${encodeURIComponent(competitionId)}` : "";
      return unwrap(
        apiClient(`staff/ballots${query}`, { ...(signal ? { signal } : {}) }).json<{
          data: BallotSummary[];
        }>(),
      );
    },
  });
}

export function useBallot(ballotId: string | undefined): UseQueryResult<Ballot, ApiError> {
  return useQuery<Ballot, ApiError>({
    enabled: Boolean(ballotId),
    queryKey: ballotKeys.detail(ballotId ?? ""),
    queryFn: ({ signal }) =>
      unwrap(
        apiClient(`staff/ballots/${ballotId}`, { ...(signal ? { signal } : {}) }).json<{
          data: Ballot;
        }>(),
      ),
    // The organizer watches the count climb while the hall votes.
    refetchInterval: (query) => (query.state.data?.status === "OPEN" ? 10_000 : false),
  });
}

/**
 * Shared plumbing for every write that answers with the whole ballot.
 *
 * The response goes into the cache directly, so the editor is exact immediately
 * rather than after a round trip it does not need.
 */
function useBallotMutation<TVariables>(
  send: (variables: TVariables) => Promise<{ data: Ballot }>,
): UseMutationResult<Ballot, ApiError, TVariables> {
  const queryClient = useQueryClient();
  return useMutation<Ballot, ApiError, TVariables>({
    mutationFn: (variables) => unwrap(send(variables)),
    onSuccess: (ballot) => {
      queryClient.setQueryData(ballotKeys.detail(ballot.id), ballot);
      void queryClient.invalidateQueries({ queryKey: ballotKeys.all });
    },
  });
}

export function useCreateBallot(): UseMutationResult<Ballot, ApiError, CreateBallotInput> {
  const queryClient = useQueryClient();
  return useMutation<Ballot, ApiError, CreateBallotInput>({
    mutationFn: (input) =>
      unwrap(apiClient("staff/ballots", { method: "post", json: input }).json<{ data: Ballot }>()),
    onSuccess: (ballot) => {
      queryClient.setQueryData(ballotKeys.detail(ballot.id), ballot);
      void queryClient.invalidateQueries({ queryKey: ballotKeys.all });
    },
  });
}

export function useUpdateBallot(
  ballotId: string,
): UseMutationResult<Ballot, ApiError, UpdateBallotInput> {
  return useBallotMutation((input) =>
    apiClient(`staff/ballots/${ballotId}`, { method: "patch", json: input }).json<{
      data: Ballot;
    }>(),
  );
}

export function useOpenBallot(ballotId: string): UseMutationResult<Ballot, ApiError, void> {
  return useBallotMutation(() =>
    apiClient(`staff/ballots/${ballotId}/open`, { method: "post" }).json<{ data: Ballot }>(),
  );
}

export function useCloseBallot(ballotId: string): UseMutationResult<Ballot, ApiError, void> {
  return useBallotMutation(() =>
    apiClient(`staff/ballots/${ballotId}/close`, { method: "post" }).json<{ data: Ballot }>(),
  );
}

export function useAddNominee(ballotId: string): UseMutationResult<Ballot, ApiError, NomineeInput> {
  return useBallotMutation((input) =>
    apiClient(`staff/ballots/${ballotId}/nominees`, { method: "post", json: input }).json<{
      data: Ballot;
    }>(),
  );
}

export function useEditNominee(
  ballotId: string,
): UseMutationResult<Ballot, ApiError, { nomineeId: string } & Partial<NomineeInput>> {
  return useBallotMutation(({ nomineeId, ...input }) =>
    apiClient(`staff/ballots/${ballotId}/nominees/${nomineeId}`, {
      method: "patch",
      json: input,
    }).json<{ data: Ballot }>(),
  );
}

export function useRemoveNominee(ballotId: string): UseMutationResult<Ballot, ApiError, string> {
  return useBallotMutation((nomineeId) =>
    apiClient(`staff/ballots/${ballotId}/nominees/${nomineeId}`, { method: "delete" }).json<{
      data: Ballot;
    }>(),
  );
}

export function useReorderNominees(
  ballotId: string,
): UseMutationResult<Ballot, ApiError, string[]> {
  return useBallotMutation((order) =>
    apiClient(`staff/ballots/${ballotId}/nominees/order`, {
      method: "post",
      json: { order },
    }).json<{
      data: Ballot;
    }>(),
  );
}

export function useDeleteBallot(): UseMutationResult<void, ApiError, string> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: async (ballotId) => {
      try {
        await apiClient(`staff/ballots/${ballotId}`, { method: "delete" });
      } catch (error) {
        throw await toApiError(error);
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ballotKeys.all });
    },
  });
}

/**
 * The running orders this ballot can be filled from.
 *
 * Empty for a standalone ballot — not an error, just a fact about it, and the
 * editor answers it by offering the file import instead.
 */
export function useBallotPrograms(
  ballotId: string,
  { enabled = true }: { enabled?: boolean } = {},
): UseQueryResult<ProgramOption[], ApiError> {
  return useQuery<ProgramOption[], ApiError>({
    enabled,
    queryKey: ballotKeys.programs(ballotId),
    queryFn: ({ signal }) =>
      unwrap(
        apiClient(`staff/ballots/${ballotId}/programs`, { ...(signal ? { signal } : {}) }).json<{
          data: ProgramOption[];
        }>(),
      ),
  });
}

/**
 * Copy a programme's acts onto the ballot as its own nominees.
 *
 * Idempotent in the way that matters on the day: seeding again after the running
 * order changed adds what is new rather than doubling what is there.
 */
export function useSeedFromProgram(ballotId: string): UseMutationResult<Ballot, ApiError, string> {
  return useBallotMutation((programId) =>
    apiClient(`staff/ballots/${ballotId}/seed`, { method: "post", json: { programId } }).json<{
      data: Ballot;
    }>(),
  );
}

/**
 * Send a filled-in spreadsheet, as a preview or for real.
 *
 * The preview is not optional politeness: an import that pours 150 rows of
 * somebody else's formatting into a ballot is one that gets undone by hand.
 */
export function useImportNominees(
  ballotId: string,
): UseMutationResult<ImportPreview, ApiError, { file: File; dryRun: boolean }> {
  const queryClient = useQueryClient();
  return useMutation<ImportPreview, ApiError, { file: File; dryRun: boolean }>({
    mutationFn: async ({ file, dryRun }) => {
      const body = new FormData();
      body.append("file", file);
      const query = dryRun ? "?dryRun=true" : "";
      return unwrap(
        apiClient(`staff/ballots/${ballotId}/nominees/import${query}`, {
          method: "post",
          body,
        }).json<{
          data: ImportPreview;
        }>(),
      );
    },
    onSuccess: (preview) => {
      if (!preview.dryRun) {
        void queryClient.invalidateQueries({ queryKey: ballotKeys.detail(ballotId) });
      }
    },
  });
}

/** The URL a download link points at. Built here so the paths live in one place. */
export function ballotDownloadUrl(ballotId: string, what: "template" | "results" | "qr"): string {
  const paths = {
    template: `staff/ballots/${ballotId}/nominees/template.xlsx`,
    results: `staff/ballots/${ballotId}/results.xlsx`,
    qr: `staff/ballots/${ballotId}/qr.png`,
  } as const;
  return paths[what];
}
