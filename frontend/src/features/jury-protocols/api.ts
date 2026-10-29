/**
 * Data access for the jury's protocols (organizer side).
 *
 * Every write returns the whole protocol, so each mutation seeds the detail cache from its
 * own response instead of refetching: a saved award changes whether the protocol can be
 * published and whether what is public is stale, and this way the screen can never show a
 * result it did not save.
 *
 * Publication is the exception, and deliberately so. Pressing that button has three
 * effects and only one of them is quick, so it answers with the published protocol *and*
 * a job: the page is public by the time the response arrives, while the diplomas and the
 * letters are issued by a worker and reported on that job ({@link usePublicationJob}).
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
  AwardEntry,
  CreateProtocolInput,
  Protocol,
  ProtocolCandidate,
  ProtocolSummary,
  PublicationJob,
  PublicationStarted,
  PublishProtocolInput,
  UpdateProtocolInput,
} from "./model";
import { isPublicationRunning } from "./model";

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

export const protocolKeys = {
  all: ["protocols"] as const,
  list: (competitionId: string) => [...protocolKeys.all, "list", competitionId] as const,
  detail: (protocolId: string) => [...protocolKeys.all, "detail", protocolId] as const,
  candidates: (protocolId: string) => [...protocolKeys.all, "candidates", protocolId] as const,
  publication: (protocolId: string) => [...protocolKeys.all, "publication", protocolId] as const,
};

export async function fetchProtocols(competitionId: string): Promise<ProtocolSummary[]> {
  const params = new URLSearchParams({ competitionId });
  const body = await request<Envelope<ProtocolSummary[]>>(`staff/protocols?${params.toString()}`);
  return body.data;
}

export async function fetchProtocol(protocolId: string): Promise<Protocol> {
  const body = await request<Envelope<Protocol>>(`staff/protocols/${protocolId}`);
  return body.data;
}

export async function fetchProtocolCandidates(protocolId: string): Promise<ProtocolCandidate[]> {
  const body = await request<Envelope<ProtocolCandidate[]>>(
    `staff/protocols/${protocolId}/candidates`,
  );
  return body.data;
}

export function useProtocols(
  competitionId: string | undefined,
): UseQueryResult<ProtocolSummary[], ApiError> {
  return useQuery<ProtocolSummary[], ApiError>({
    enabled: Boolean(competitionId),
    queryKey: protocolKeys.list(competitionId ?? ""),
    queryFn: () => fetchProtocols(competitionId ?? ""),
  });
}

export function useProtocol(protocolId: string | null): UseQueryResult<Protocol, ApiError> {
  return useQuery<Protocol, ApiError>({
    enabled: protocolId != null,
    queryKey: protocolKeys.detail(protocolId ?? ""),
    queryFn: () => fetchProtocol(protocolId ?? ""),
  });
}

export function useProtocolCandidates(
  protocolId: string | null,
): UseQueryResult<ProtocolCandidate[], ApiError> {
  return useQuery<ProtocolCandidate[], ApiError>({
    enabled: protocolId != null,
    queryKey: protocolKeys.candidates(protocolId ?? ""),
    queryFn: () => fetchProtocolCandidates(protocolId ?? ""),
  });
}

/**
 * Shared plumbing for every write on one protocol.
 *
 * The response *is* the new state: it is written straight into the detail cache, and the
 * candidate list plus the protocol list are invalidated because a row added here is a
 * candidate consumed there, and a result entered here moves the list's progress count.
 */
function useProtocolMutation<TVariables>(
  send: (variables: TVariables) => Promise<Envelope<Protocol>>,
): UseMutationResult<Protocol, ApiError, TVariables> {
  const queryClient = useQueryClient();
  return useMutation<Protocol, ApiError, TVariables>({
    mutationFn: async (variables) => (await send(variables)).data,
    onSuccess: (protocol) => {
      queryClient.setQueryData(protocolKeys.detail(protocol.id), protocol);
      void queryClient.invalidateQueries({ queryKey: protocolKeys.candidates(protocol.id) });
      void queryClient.invalidateQueries({ queryKey: [...protocolKeys.all, "list"] });
    },
  });
}

export function useCreateProtocol(): UseMutationResult<Protocol, ApiError, CreateProtocolInput> {
  const queryClient = useQueryClient();
  return useMutation<Protocol, ApiError, CreateProtocolInput>({
    mutationFn: async (input) =>
      (await request<Envelope<Protocol>>("staff/protocols", { method: "post", json: input })).data,
    onSuccess: (protocol) => {
      queryClient.setQueryData(protocolKeys.detail(protocol.id), protocol);
      void queryClient.invalidateQueries({ queryKey: [...protocolKeys.all, "list"] });
    },
  });
}

export function useUpdateProtocol(
  protocolId: string,
): UseMutationResult<Protocol, ApiError, UpdateProtocolInput> {
  return useProtocolMutation<UpdateProtocolInput>((input) =>
    request<Envelope<Protocol>>(`staff/protocols/${protocolId}`, { method: "patch", json: input }),
  );
}

export function useDeleteProtocol(): UseMutationResult<void, ApiError, string> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: async (protocolId) => {
      // 204 No Content: there is no body to parse here.
      try {
        await apiClient(`staff/protocols/${protocolId}`, { method: "delete" });
      } catch (error) {
        throw await toApiError(error);
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: protocolKeys.all });
    },
  });
}

/** Add one act's line by hand — the number slotted in on the day. */
export function useAddProtocolRow(
  protocolId: string,
): UseMutationResult<Protocol, ApiError, { submissionId: string; position?: number }> {
  return useProtocolMutation((input) =>
    request<Envelope<Protocol>>(`staff/protocols/${protocolId}/rows`, {
      method: "post",
      json: input,
    }),
  );
}

/**
 * Pull in every act of this nomination that has no row yet.
 *
 * Append-only on the backend: existing rows keep their place and their award, so this is
 * safe to press after results have been entered.
 */
export function useSyncProtocolRows(
  protocolId: string,
): UseMutationResult<Protocol, ApiError, void> {
  return useProtocolMutation<void>(() =>
    request<Envelope<Protocol>>(`staff/protocols/${protocolId}/rows/sync`, { method: "post" }),
  );
}

export function useRemoveProtocolRow(
  protocolId: string,
): UseMutationResult<Protocol, ApiError, string> {
  return useProtocolMutation<string>((rowId) =>
    request<Envelope<Protocol>>(`staff/protocols/${protocolId}/rows/${rowId}`, {
      method: "delete",
    }),
  );
}

/** Send the complete new order. Numbers stay with the acts they belong to. */
export function useReorderProtocolRows(
  protocolId: string,
): UseMutationResult<Protocol, ApiError, string[]> {
  return useProtocolMutation<string[]>((rowIds) =>
    request<Envelope<Protocol>>(`staff/protocols/${protocolId}/rows/order`, {
      method: "put",
      json: { rowIds },
    }),
  );
}

/**
 * Re-issue numbers 1..N along the current order.
 *
 * Its own call rather than part of a reorder: it invalidates every number already told to a
 * participant, so it has to be something the organizer asks for.
 */
export function useRenumberProtocolRows(
  protocolId: string,
): UseMutationResult<Protocol, ApiError, void> {
  return useProtocolMutation<void>(() =>
    request<Envelope<Protocol>>(`staff/protocols/${protocolId}/rows/numbers`, { method: "post" }),
  );
}

/**
 * Write results — one, or a whole nomination's worth in a single save.
 *
 * The call the jury tab exists for, and deliberately unremarkable: no confirmation, no
 * one-way transition. `award: null` in an entry clears that row.
 */
export function useAwardProtocolRows(
  protocolId: string,
): UseMutationResult<Protocol, ApiError, AwardEntry[]> {
  return useProtocolMutation<AwardEntry[]>((awards) =>
    request<Envelope<Protocol>>(`staff/protocols/${protocolId}/awards`, {
      method: "put",
      json: { awards },
    }),
  );
}

export function useClearProtocolAwards(
  protocolId: string,
): UseMutationResult<Protocol, ApiError, void> {
  return useProtocolMutation<void>(() =>
    request<Envelope<Protocol>>(`staff/protocols/${protocolId}/awards`, { method: "delete" }),
  );
}

/**
 * Publish the results: the public page first, the diplomas and the letters after.
 *
 * Answers as soon as the page is public — which is what the organizer pressed the button
 * for — with the protocol in its final published state and a job to follow. The rest is a
 * worker's: a diploma is rendered per awarded row (and per named member of a collective on
 * top of that), so a nomination of a hundred and fifty acts outlasts anything between the
 * browser and the backend willing to hold a connection open. It used to be done inside the
 * request, and a real festival was shown «Не удалось опубликовать протокол» on a protocol
 * the server had published.
 *
 * The detail cache is seeded from the response and the publication query is primed with the
 * job, so {@link usePublicationJob} starts polling an already-known run rather than a blank.
 */
export function usePublishProtocol(
  protocolId: string,
): UseMutationResult<PublicationStarted, ApiError, PublishProtocolInput> {
  const queryClient = useQueryClient();
  return useMutation<PublicationStarted, ApiError, PublishProtocolInput>({
    mutationFn: async (input) =>
      (
        await request<Envelope<PublicationStarted>>(`staff/protocols/${protocolId}/publication`, {
          method: "post",
          json: input,
        })
      ).data,
    onSuccess: (started) => {
      queryClient.setQueryData(protocolKeys.detail(started.protocol.id), started.protocol);
      queryClient.setQueryData(protocolKeys.publication(started.protocol.id), started.job);
      void queryClient.invalidateQueries({ queryKey: [...protocolKeys.all, "list"] });
    },
  });
}

async function fetchPublicationJob(protocolId: string): Promise<PublicationJob | null> {
  const body = await request<Envelope<PublicationJob | null>>(
    `staff/protocols/${protocolId}/publication`,
  );
  return body.data;
}

/**
 * Follow the publication a protocol last started: the diplomas, the letters, a failure.
 *
 * Polled while the run is unfinished and left alone once it settles. Keyed by protocol
 * rather than by job id on purpose — the screen always has the protocol, so an organizer
 * who reloads the page mid-run picks the run back up instead of losing it. `null` means
 * this protocol has never been published, which is a normal answer, not a missing one.
 */
export function usePublicationJob(
  protocolId: string | null,
): UseQueryResult<PublicationJob | null, ApiError> {
  return useQuery<PublicationJob | null, ApiError>({
    enabled: protocolId != null,
    queryKey: protocolKeys.publication(protocolId ?? ""),
    queryFn: () => fetchPublicationJob(protocolId ?? ""),
    refetchInterval: (query) => (isPublicationRunning(query.state.data) ? 2500 : false),
  });
}

/** Take a protocol back off the public page. The diplomas already issued stay issued. */
export function useUnpublishProtocol(
  protocolId: string,
): UseMutationResult<Protocol, ApiError, void> {
  return useProtocolMutation<void>(() =>
    request<Envelope<Protocol>>(`staff/protocols/${protocolId}/publication`, { method: "delete" }),
  );
}
