/**
 * Data access for the programme constructor (organizer side).
 *
 * Every write returns the whole recomputed programme, so each mutation seeds the
 * detail cache from its own response instead of refetching: inserting a break moves
 * every later start time, and this way the UI can never show a stale timetable.
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
  AddBlockInput,
  CreateProgramInput,
  CreateShareInput,
  Program,
  ProgramCandidate,
  ProgramColumnKey,
  ProgramShare,
  ProgramSummary,
  UpdateProgramInput,
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

export const programKeys = {
  all: ["programs"] as const,
  list: (competitionId: string, nominationId?: string | null) =>
    [...programKeys.all, "list", competitionId, nominationId ?? "all"] as const,
  detail: (programId: string) => [...programKeys.all, "detail", programId] as const,
  candidates: (programId: string) => [...programKeys.all, "candidates", programId] as const,
};

export async function fetchPrograms(
  competitionId: string,
  nominationId?: string | null,
): Promise<ProgramSummary[]> {
  const params = new URLSearchParams({ competitionId });
  if (nominationId) {
    params.set("nominationId", nominationId);
  }
  const body = await request<Envelope<ProgramSummary[]>>(`staff/programs?${params.toString()}`);
  return body.data;
}

export async function fetchProgram(programId: string): Promise<Program> {
  const body = await request<Envelope<Program>>(`staff/programs/${programId}`);
  return body.data;
}

export async function fetchCandidates(programId: string): Promise<ProgramCandidate[]> {
  const body = await request<Envelope<ProgramCandidate[]>>(
    `staff/programs/${programId}/candidates`,
  );
  return body.data;
}

export function usePrograms(
  competitionId: string | undefined,
  nominationId?: string | null,
): UseQueryResult<ProgramSummary[], ApiError> {
  return useQuery<ProgramSummary[], ApiError>({
    enabled: Boolean(competitionId),
    queryKey: programKeys.list(competitionId ?? "", nominationId),
    queryFn: () => fetchPrograms(competitionId ?? "", nominationId),
  });
}

export function useProgram(programId: string | null): UseQueryResult<Program, ApiError> {
  return useQuery<Program, ApiError>({
    enabled: programId != null,
    queryKey: programKeys.detail(programId ?? ""),
    queryFn: () => fetchProgram(programId ?? ""),
  });
}

export function useProgramCandidates(
  programId: string | null,
): UseQueryResult<ProgramCandidate[], ApiError> {
  return useQuery<ProgramCandidate[], ApiError>({
    enabled: programId != null,
    queryKey: programKeys.candidates(programId ?? ""),
    queryFn: () => fetchCandidates(programId ?? ""),
  });
}

/**
 * Shared plumbing for every write on one programme.
 *
 * The response *is* the new state: it is written straight into the detail cache, and
 * the candidate list plus the programme list are invalidated because a slot added here
 * is a candidate consumed there.
 */
function useProgramMutation<TVariables>(
  send: (variables: TVariables) => Promise<Envelope<Program>>,
): UseMutationResult<Program, ApiError, TVariables> {
  const queryClient = useQueryClient();
  return useMutation<Program, ApiError, TVariables>({
    mutationFn: async (variables) => (await send(variables)).data,
    onSuccess: (program) => {
      queryClient.setQueryData(programKeys.detail(program.id), program);
      void queryClient.invalidateQueries({ queryKey: programKeys.candidates(program.id) });
      void queryClient.invalidateQueries({
        queryKey: [...programKeys.all, "list"],
      });
    },
  });
}

export function useCreateProgram(): UseMutationResult<Program, ApiError, CreateProgramInput> {
  const queryClient = useQueryClient();
  return useMutation<Program, ApiError, CreateProgramInput>({
    mutationFn: async (input) =>
      (
        await request<Envelope<Program>>("staff/programs", {
          method: "post",
          json: input,
        })
      ).data,
    onSuccess: (program) => {
      queryClient.setQueryData(programKeys.detail(program.id), program);
      void queryClient.invalidateQueries({ queryKey: [...programKeys.all, "list"] });
    },
  });
}

export function useUpdateProgram(
  programId: string,
): UseMutationResult<Program, ApiError, UpdateProgramInput> {
  return useProgramMutation<UpdateProgramInput>((input) =>
    request<Envelope<Program>>(`staff/programs/${programId}`, { method: "patch", json: input }),
  );
}

export function useDeleteProgram(): UseMutationResult<void, ApiError, string> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: async (programId) => {
      // 204 No Content: there is no body to parse here.
      try {
        await apiClient(`staff/programs/${programId}`, { method: "delete" });
      } catch (error) {
        throw await toApiError(error);
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: programKeys.all });
    },
  });
}

/** Give one competing act a slot. */
export function useAddPerformance(
  programId: string,
): UseMutationResult<Program, ApiError, { submissionId: string; position?: number }> {
  return useProgramMutation((input) =>
    request<Envelope<Program>>(`staff/programs/${programId}/items`, {
      method: "post",
      json: input,
    }),
  );
}

/** Append every remaining competing act of the programme's scope. */
export function useFillProgram(programId: string): UseMutationResult<Program, ApiError, void> {
  return useProgramMutation<void>(() =>
    request<Envelope<Program>>(`staff/programs/${programId}/items/fill`, { method: "post" }),
  );
}

/** Insert a break (or any other standalone block). */
export function useAddBlock(
  programId: string,
): UseMutationResult<Program, ApiError, AddBlockInput> {
  return useProgramMutation<AddBlockInput>((input) =>
    request<Envelope<Program>>(`staff/programs/${programId}/items`, {
      method: "post",
      json: input,
    }),
  );
}

export function useEditItem(
  programId: string,
): UseMutationResult<
  Program,
  ApiError,
  { itemId: string; title?: string; durationSeconds?: number }
> {
  return useProgramMutation(({ itemId, ...body }) =>
    request<Envelope<Program>>(`staff/programs/${programId}/items/${itemId}`, {
      method: "patch",
      json: body,
    }),
  );
}

export function useRemoveItem(programId: string): UseMutationResult<Program, ApiError, string> {
  return useProgramMutation<string>((itemId) =>
    request<Envelope<Program>>(`staff/programs/${programId}/items/${itemId}`, {
      method: "delete",
    }),
  );
}

/** Send the complete new running order. Permanent numbers stay with their slots. */
export function useReorderItems(programId: string): UseMutationResult<Program, ApiError, string[]> {
  return useProgramMutation<string[]>((itemIds) =>
    request<Envelope<Program>>(`staff/programs/${programId}/items/order`, {
      method: "put",
      json: { itemIds },
    }),
  );
}

/**
 * Re-issue numbers 1..N along the current order.
 *
 * Deliberately its own call rather than part of a reorder: it invalidates every number
 * already told to a participant, so it has to be something the organizer asks for.
 */
export function useRenumberItems(programId: string): UseMutationResult<Program, ApiError, void> {
  return useProgramMutation<void>(() =>
    request<Envelope<Program>>(`staff/programs/${programId}/items/numbers`, { method: "post" }),
  );
}

/**
 * Publish a named edition of the programme.
 *
 * ``columns`` is the selection that defines it — which columns of the table its reader
 * sees. An empty row selection publishes every row, now and as the programme grows.
 */
export function useCreateShare(
  programId: string,
): UseMutationResult<ProgramShare, ApiError, CreateShareInput> {
  const queryClient = useQueryClient();
  return useMutation<ProgramShare, ApiError, CreateShareInput>({
    mutationFn: async (input) => {
      const body = await request<Envelope<{ share: ProgramShare; program: Program }>>(
        `staff/programs/${programId}/shares`,
        { method: "post", json: input },
      );
      queryClient.setQueryData(programKeys.detail(programId), body.data.program);
      return body.data.share;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: [...programKeys.all, "list"] });
    },
  });
}

/** Change which columns a live link shows (or rename it) — its slug is permanent. */
export function useUpdateShare(
  programId: string,
): UseMutationResult<
  ProgramShare,
  ApiError,
  { shareId: string; name?: string; columns?: ProgramColumnKey[] }
> {
  const queryClient = useQueryClient();
  return useMutation<
    ProgramShare,
    ApiError,
    { shareId: string; name?: string; columns?: ProgramColumnKey[] }
  >({
    mutationFn: async ({ shareId, ...body }) => {
      const response = await request<Envelope<{ share: ProgramShare; program: Program }>>(
        `staff/programs/${programId}/shares/${shareId}`,
        { method: "patch", json: body },
      );
      queryClient.setQueryData(programKeys.detail(programId), response.data.program);
      return response.data.share;
    },
  });
}

/** Revoke an edition — its link stops resolving at once. */
export function useRemoveShare(programId: string): UseMutationResult<Program, ApiError, string> {
  return useProgramMutation<string>((shareId) =>
    request<Envelope<Program>>(`staff/programs/${programId}/shares/${shareId}`, {
      method: "delete",
    }),
  );
}
