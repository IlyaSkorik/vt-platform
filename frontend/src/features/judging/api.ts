/**
 * Data access for online judging.
 *
 * Three audiences share this module, and their caches are kept apart on purpose:
 * `judgingKeys.setup` is the organizer's configuration, `judgingKeys.tasks` a judge's
 * own list, `judgingKeys.board` the hall's screen.
 *
 * Every configuration write answers with the whole setup, so each mutation seeds the
 * cache from its own response instead of refetching: editing a criterion changes
 * whether the festival is ready to be judged, and a screen that refetched separately
 * would flicker through a state that was never true.
 *
 * The two live reads — a judge's tasks and the board — poll. There is no WebSocket in
 * the platform yet (ARCH-001 §11 puts Channels in a later phase), and polling is what
 * the audience-vote board already does beside the same stage.
 */
import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { type ApiError, apiClient, toApiError } from "@/shared/api";

import type {
  AssignJuryInput,
  AwardScaleInput,
  Board,
  BoardInput,
  CriteriaInput,
  InviteJuryInput,
  JudgingSetup,
  JuryMember,
  JurySeat,
  JuryTask,
  RunningOrderEntry,
  ScoringRulesInput,
  ScoringState,
  ScoringStateInput,
  SubmitScorecardInput,
  TallyApplication,
  TallyScopeInput,
  TallySheet,
  UpdateJuryInput,
} from "./model";

interface Envelope<T> {
  data: T;
  meta?: { total?: number; requestId?: string };
}

async function request<T>(path: string, options?: Parameters<typeof apiClient>[1]): Promise<T> {
  try {
    return await apiClient(path, options).json<T>();
  } catch (error) {
    throw await toApiError(error);
  }
}

/**
 * How often a live screen asks again.
 *
 * Four seconds is the compromise the vote board already settled on: fast enough that a
 * mark appears while the applause is still going, slow enough that a hall of tablets
 * plus a projector is a handful of requests a second rather than a load test.
 */
const LIVE_REFETCH_MS = 4_000;

function isHidden(): boolean {
  return typeof document !== "undefined" && document.visibilityState === "hidden";
}

export const judgingKeys = {
  all: ["judging"] as const,
  setup: (competitionId: string) => [...judgingKeys.all, "setup", competitionId] as const,
  jury: (competitionId: string) => [...judgingKeys.all, "jury", competitionId] as const,
  tally: (competitionId: string) => [...judgingKeys.all, "tally", competitionId] as const,
  states: (competitionId: string) => [...judgingKeys.all, "states", competitionId] as const,
  tasks: (competitionId: string) => [...judgingKeys.all, "tasks", competitionId] as const,
  seats: () => [...judgingKeys.all, "seats"] as const,
  runningOrder: (competitionId: string) =>
    [...judgingKeys.all, "running-order", competitionId] as const,
  board: (slug: string) => [...judgingKeys.all, "board", slug] as const,
};

// ---------------------------------------------------------------------------
// The organizer's configuration
// ---------------------------------------------------------------------------

export async function fetchJudgingSetup(competitionId: string): Promise<JudgingSetup> {
  const params = new URLSearchParams({ competitionId });
  const body = await request<Envelope<JudgingSetup>>(`staff/judging/setup?${params.toString()}`);
  return body.data;
}

export function useJudgingSetup(
  competitionId: string | undefined,
): UseQueryResult<JudgingSetup, ApiError> {
  return useQuery<JudgingSetup, ApiError>({
    enabled: Boolean(competitionId),
    queryKey: judgingKeys.setup(competitionId ?? ""),
    queryFn: () => fetchJudgingSetup(competitionId ?? ""),
  });
}

/**
 * Shared plumbing for every configuration write.
 *
 * The response *is* the new configuration, so it goes straight into the cache. The
 * tally is invalidated alongside it because changing criteria, rules or bands changes
 * every number on that screen.
 */
function useSetupMutation<TVariables extends { competitionId: string }>(
  send: (variables: TVariables) => Promise<Envelope<JudgingSetup>>,
): UseMutationResult<JudgingSetup, ApiError, TVariables> {
  const queryClient = useQueryClient();
  return useMutation<JudgingSetup, ApiError, TVariables>({
    mutationFn: async (variables) => (await send(variables)).data,
    onSuccess: (setup) => {
      queryClient.setQueryData(judgingKeys.setup(setup.competitionId), setup);
      void queryClient.invalidateQueries({ queryKey: judgingKeys.tally(setup.competitionId) });
    },
  });
}

export function useReplaceCriteria(): UseMutationResult<JudgingSetup, ApiError, CriteriaInput> {
  return useSetupMutation<CriteriaInput>((input) =>
    request<Envelope<JudgingSetup>>("staff/judging/criteria", { method: "put", json: input }),
  );
}

export function useReplaceAwardScale(): UseMutationResult<JudgingSetup, ApiError, AwardScaleInput> {
  return useSetupMutation<AwardScaleInput>((input) =>
    request<Envelope<JudgingSetup>>("staff/judging/award-scale", { method: "put", json: input }),
  );
}

export function useUpdateScoringRules(): UseMutationResult<
  JudgingSetup,
  ApiError,
  ScoringRulesInput
> {
  return useSetupMutation<ScoringRulesInput>((input) =>
    request<Envelope<JudgingSetup>>("staff/judging/scoring-rules", { method: "put", json: input }),
  );
}

export function useUpdateTallyScope(): UseMutationResult<JudgingSetup, ApiError, TallyScopeInput> {
  return useSetupMutation<TallyScopeInput>((input) =>
    request<Envelope<JudgingSetup>>("staff/judging/tally-scope", { method: "put", json: input }),
  );
}

export function useUpdateBoardSettings(): UseMutationResult<JudgingSetup, ApiError, BoardInput> {
  return useSetupMutation<BoardInput>((input) =>
    request<Envelope<JudgingSetup>>("staff/judging/board", { method: "put", json: input }),
  );
}

// ---------------------------------------------------------------------------
// The panel
// ---------------------------------------------------------------------------

export async function fetchJury(competitionId: string): Promise<JuryMember[]> {
  const params = new URLSearchParams({ competitionId });
  const body = await request<Envelope<JuryMember[]>>(`staff/judging/jury?${params.toString()}`);
  return body.data;
}

export function useJury(competitionId: string | undefined): UseQueryResult<JuryMember[], ApiError> {
  return useQuery<JuryMember[], ApiError>({
    enabled: Boolean(competitionId),
    queryKey: judgingKeys.jury(competitionId ?? ""),
    queryFn: () => fetchJury(competitionId ?? ""),
  });
}

/**
 * Shared plumbing for every write on the panel.
 *
 * Both the jury list and the setup are invalidated: the setup screen prints how many
 * judges there are, and that is exactly the number this changes.
 */
function useJuryMutation<TVariables>(
  competitionId: string,
  send: (variables: TVariables) => Promise<unknown>,
): UseMutationResult<unknown, ApiError, TVariables> {
  const queryClient = useQueryClient();
  return useMutation<unknown, ApiError, TVariables>({
    mutationFn: (variables) => send(variables),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: judgingKeys.jury(competitionId) });
      void queryClient.invalidateQueries({ queryKey: judgingKeys.setup(competitionId) });
      void queryClient.invalidateQueries({ queryKey: judgingKeys.tally(competitionId) });
    },
  });
}

export function useInviteJuryMember(
  competitionId: string,
): UseMutationResult<unknown, ApiError, InviteJuryInput> {
  return useJuryMutation<InviteJuryInput>(competitionId, (input) =>
    request<Envelope<JuryMember>>("staff/judging/jury", { method: "post", json: input }),
  );
}

export function useUpdateJuryMember(
  competitionId: string,
): UseMutationResult<unknown, ApiError, UpdateJuryInput> {
  return useJuryMutation<UpdateJuryInput>(competitionId, ({ memberId, ...input }) =>
    request<Envelope<JuryMember>>(`staff/judging/jury/${memberId}`, {
      method: "patch",
      json: input,
    }),
  );
}

export function useAssignJuryMember(
  competitionId: string,
): UseMutationResult<unknown, ApiError, AssignJuryInput> {
  return useJuryMutation<AssignJuryInput>(competitionId, ({ memberId, categoryIds }) =>
    request<Envelope<JuryMember>>(`staff/judging/jury/${memberId}/assignments`, {
      method: "put",
      json: { categoryIds },
    }),
  );
}

export function useReinviteJuryMember(
  competitionId: string,
): UseMutationResult<unknown, ApiError, string> {
  return useJuryMutation<string>(competitionId, (memberId) =>
    request<Envelope<JuryMember>>(`staff/judging/jury/${memberId}/reinvite`, { method: "post" }),
  );
}

export function useRevokeJuryMember(
  competitionId: string,
): UseMutationResult<unknown, ApiError, string> {
  return useJuryMutation<string>(competitionId, (memberId) =>
    request<Envelope<JuryMember>>(`staff/judging/jury/${memberId}/revoke`, { method: "post" }),
  );
}

export function useRemoveJuryMember(
  competitionId: string,
): UseMutationResult<unknown, ApiError, string> {
  return useJuryMutation<string>(competitionId, async (memberId) => {
    // 204 No Content: there is no body to parse here.
    try {
      await apiClient(`staff/judging/jury/${memberId}`, { method: "delete" });
    } catch (error) {
      throw await toApiError(error);
    }
  });
}

// ---------------------------------------------------------------------------
// The day itself
// ---------------------------------------------------------------------------

export async function fetchScoringStates(competitionId: string): Promise<ScoringState[]> {
  const params = new URLSearchParams({ competitionId });
  const body = await request<Envelope<ScoringState[]>>(
    `staff/judging/scoring?${params.toString()}`,
  );
  return body.data;
}

/**
 * The host's own screen.
 *
 * Polls while visible: the host is not the only person who can open an act — a second
 * organizer at the back of the hall may be driving the same programme — and a stale
 * "сейчас на сцене" is how two people close each other's acts.
 */
export function useScoringStates(
  competitionId: string | undefined,
  { live = false }: { live?: boolean } = {},
): UseQueryResult<ScoringState[], ApiError> {
  return useQuery<ScoringState[], ApiError>({
    enabled: Boolean(competitionId),
    queryKey: judgingKeys.states(competitionId ?? ""),
    queryFn: () => fetchScoringStates(competitionId ?? ""),
    refetchInterval: () => (live && !isHidden() ? LIVE_REFETCH_MS : false),
  });
}

export async function fetchRunningOrder(competitionId: string): Promise<RunningOrderEntry[]> {
  const params = new URLSearchParams({ competitionId });
  const body = await request<Envelope<RunningOrderEntry[]>>(
    `staff/judging/running-order?${params.toString()}`,
  );
  return body.data;
}

/**
 * The programme in programme order — what the host announces from.
 *
 * Deliberately not the tally. A tally sorts by score so results read top-down; a host
 * reads down the running order, and a list that reshuffles every time an act is marked
 * is one they stop trusting by the third number.
 */
export function useRunningOrder(
  competitionId: string | undefined,
  { live = false }: { live?: boolean } = {},
): UseQueryResult<RunningOrderEntry[], ApiError> {
  return useQuery<RunningOrderEntry[], ApiError>({
    enabled: Boolean(competitionId),
    queryKey: judgingKeys.runningOrder(competitionId ?? ""),
    queryFn: () => fetchRunningOrder(competitionId ?? ""),
    refetchInterval: () => (live && !isHidden() ? LIVE_REFETCH_MS : false),
  });
}

function useScoringMutation(
  competitionId: string,
  path: string,
): UseMutationResult<ScoringState, ApiError, ScoringStateInput> {
  const queryClient = useQueryClient();
  return useMutation<ScoringState, ApiError, ScoringStateInput>({
    mutationFn: async (input) =>
      (await request<Envelope<ScoringState>>(path, { method: "post", json: input })).data,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: judgingKeys.states(competitionId) });
      void queryClient.invalidateQueries({ queryKey: judgingKeys.runningOrder(competitionId) });
      void queryClient.invalidateQueries({ queryKey: judgingKeys.tally(competitionId) });
      void queryClient.invalidateQueries({ queryKey: judgingKeys.tasks(competitionId) });
    },
  });
}

export function useOpenScoring(
  competitionId: string,
): UseMutationResult<ScoringState, ApiError, ScoringStateInput> {
  return useScoringMutation(competitionId, "staff/judging/scoring/open");
}

export function useCloseScoring(
  competitionId: string,
): UseMutationResult<ScoringState, ApiError, ScoringStateInput> {
  return useScoringMutation(competitionId, "staff/judging/scoring/close");
}

// ---------------------------------------------------------------------------
// The tally
// ---------------------------------------------------------------------------

export async function fetchTally(competitionId: string): Promise<TallySheet> {
  const params = new URLSearchParams({ competitionId });
  const body = await request<Envelope<TallySheet>>(`staff/judging/tally?${params.toString()}`);
  return body.data;
}

export function useTally(
  competitionId: string | undefined,
  { live = false }: { live?: boolean } = {},
): UseQueryResult<TallySheet, ApiError> {
  return useQuery<TallySheet, ApiError>({
    enabled: Boolean(competitionId),
    queryKey: judgingKeys.tally(competitionId ?? ""),
    queryFn: () => fetchTally(competitionId ?? ""),
    refetchInterval: () => (live && !isHidden() ? LIVE_REFETCH_MS : false),
  });
}

/**
 * Write the computed awards into the protocols.
 *
 * Answers with what actually happened, not just a count. "Nothing changed" and "there
 * was no protocol to write onto" are different outcomes, and conflating them is how an
 * organizer walks to a ceremony with empty protocols believing the tally landed.
 *
 * `createMissing` opens a protocol for each genre that has none, seeded from the
 * programme — the organizer asks for that with a second press, never silently.
 */
export interface ApplyTallyInput {
  createMissing?: boolean;
}

export function useApplyTallyToProtocols(
  competitionId: string,
): UseMutationResult<TallyApplication, ApiError, ApplyTallyInput> {
  const queryClient = useQueryClient();
  return useMutation<TallyApplication, ApiError, ApplyTallyInput>({
    mutationFn: async (input) => {
      const params = new URLSearchParams({ competitionId });
      const body = await request<Envelope<TallyApplication>>(
        `staff/judging/tally/apply?${params.toString()}`,
        { method: "post", json: { createMissing: input.createMissing ?? false } },
      );
      return body.data;
    },
    onSuccess: () => {
      // The protocols tab is a different feature with its own cache; a tally push is
      // exactly the thing that makes what it is showing wrong.
      void queryClient.invalidateQueries({ queryKey: ["protocols"] });
    },
  });
}

// ---------------------------------------------------------------------------
// The judge's tablet
// ---------------------------------------------------------------------------

export async function fetchJurySeats(): Promise<JurySeat[]> {
  const body = await request<Envelope<JurySeat[]>>("jury/competitions");
  return body.data;
}

/**
 * The festivals this account judges — a judge's way back into the platform.
 *
 * Answers with an empty list for somebody who sits on no panel, which is what every
 * screen that offers the section keys off: not being a judge is not an error.
 */
export function useJurySeats(): UseQueryResult<JurySeat[], ApiError> {
  return useQuery<JurySeat[], ApiError>({
    queryKey: judgingKeys.seats(),
    queryFn: () => fetchJurySeats(),
    // A seat is granted by an organizer, not by anything this tab did; re-asking on
    // every mount puts a request behind every navigation for an answer that changes
    // once a season.
    staleTime: 5 * 60_000,
  });
}

export async function fetchJuryTasks(competitionId: string): Promise<JuryTask[]> {
  const params = new URLSearchParams({ competitionId });
  const body = await request<Envelope<JuryTask[]>>(`jury/tasks?${params.toString()}`);
  return body.data;
}

/**
 * The acts this judge is seated for.
 *
 * Polls while visible: the host opening the next act is what makes the tablet usable,
 * and a judge should not have to pull to refresh between numbers.
 */
export function useJuryTasks(
  competitionId: string | undefined,
  { live = true }: { live?: boolean } = {},
): UseQueryResult<JuryTask[], ApiError> {
  return useQuery<JuryTask[], ApiError>({
    enabled: Boolean(competitionId),
    queryKey: judgingKeys.tasks(competitionId ?? ""),
    queryFn: () => fetchJuryTasks(competitionId ?? ""),
    refetchInterval: () => (live && !isHidden() ? LIVE_REFETCH_MS : false),
  });
}

export function useSubmitScorecard(
  competitionId: string,
): UseMutationResult<JuryTask, ApiError, SubmitScorecardInput> {
  const queryClient = useQueryClient();
  return useMutation<JuryTask, ApiError, SubmitScorecardInput>({
    mutationFn: async (input) =>
      (await request<Envelope<JuryTask>>("jury/scorecards", { method: "put", json: input })).data,
    onSuccess: (task) => {
      // Patch the one act in place rather than refetching the list: a judge who has
      // just sent a sheet should see it land, not see the whole screen redraw.
      queryClient.setQueryData<JuryTask[]>(judgingKeys.tasks(competitionId), (previous) =>
        previous?.map((item) => (item.submissionId === task.submissionId ? task : item)),
      );
    },
  });
}

export function useAcceptJuryInvitation(): UseMutationResult<JuryMember, ApiError, string> {
  const queryClient = useQueryClient();
  return useMutation<JuryMember, ApiError, string>({
    mutationFn: async (token) =>
      (await request<Envelope<JuryMember>>(`jury/invitations/${token}/accept`, { method: "post" }))
        .data,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: judgingKeys.all });
    },
  });
}

// ---------------------------------------------------------------------------
// The hall's board
// ---------------------------------------------------------------------------

export async function fetchBoard(slug: string): Promise<Board> {
  const body = await request<Envelope<Board>>(`public/judging/board/${slug}`);
  return body.data;
}

/**
 * The screen beside the stage.
 *
 * Keeps polling while out of sight, unlike a judge's tablet: nothing ever brings a
 * projector back to the foreground, and it has to be right whenever somebody looks up.
 */
export function useBoard(slug: string | undefined): UseQueryResult<Board, ApiError> {
  return useQuery<Board, ApiError>({
    enabled: Boolean(slug),
    queryKey: judgingKeys.board(slug ?? ""),
    queryFn: () => fetchBoard(slug ?? ""),
    refetchInterval: LIVE_REFETCH_MS,
    refetchIntervalInBackground: true,
  });
}
