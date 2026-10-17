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

import { type ApiError, apiClient, saveAuthenticatedDownload, toApiError } from "@/shared/api";

import type {
  AddBlockInput,
  AnnounceShareInput,
  ArrangeProgramInput,
  ColumnKey,
  CreateProgramInput,
  CreateShareInput,
  Program,
  ProgramAnnouncement,
  ProgramCandidate,
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
 *
 * **One write at a time, and never backwards.** Every endpoint here answers with the
 * whole recomputed programme, so two writes in flight together are two complete and
 * mutually stale snapshots racing to land last — and the loser silently undoes the
 * winner. That is what organizers saw as «сбивается буфер»: the start time was changed
 * while the buffer's PATCH was still out, and the reply to the earlier one arrived
 * second and put the old buffer back on screen. Two guards, because either alone leaves
 * a gap:
 *
 * * `scope` makes React Query queue writes to one programme instead of running them
 *   concurrently, so each is sent against the state the previous one produced;
 * * {@link isNewer} refuses a reply older than what the cache already holds, which also
 *   covers a write started elsewhere (another tab, the host's own screen).
 */
function useProgramMutation<TVariables>(
  programId: string,
  send: (variables: TVariables) => Promise<Envelope<Program>>,
): UseMutationResult<Program, ApiError, TVariables> {
  const queryClient = useQueryClient();
  return useMutation<Program, ApiError, TVariables>({
    scope: { id: `program:${programId}` },
    mutationFn: async (variables) => (await send(variables)).data,
    onSuccess: (program) => {
      const key = programKeys.detail(program.id);
      if (isNewer(program, queryClient.getQueryData<Program>(key))) {
        queryClient.setQueryData(key, program);
      }
      void queryClient.invalidateQueries({ queryKey: programKeys.candidates(program.id) });
      void queryClient.invalidateQueries({
        queryKey: [...programKeys.all, "list"],
      });
    },
  });
}

/**
 * Whether `incoming` is worth writing over `cached`.
 *
 * The backend bumps `version` on every change to the aggregate, so a strictly lower one
 * is a snapshot from before something the cache already knows about. Equal versions pass:
 * that is an optimistic patch being confirmed by the reply it predicted, and the server's
 * copy is the one with the recomputed timetable on it.
 */
function isNewer(incoming: Program, cached: Program | undefined): boolean {
  return cached === undefined || incoming.version >= cached.version;
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
  return useProgramMutation<UpdateProgramInput>(programId, (input) =>
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
  return useProgramMutation(programId, (input) =>
    request<Envelope<Program>>(`staff/programs/${programId}/items`, {
      method: "post",
      json: input,
    }),
  );
}

/** Append every remaining competing act of the programme's scope. */
export function useFillProgram(programId: string): UseMutationResult<Program, ApiError, void> {
  return useProgramMutation<void>(programId, () =>
    request<Envelope<Program>>(`staff/programs/${programId}/items/fill`, { method: "post" }),
  );
}

/**
 * Build the whole running order from rules, replacing whatever stood there.
 *
 * Sending `undefined` is the «Пересобрать» button: an empty body tells the backend to
 * reuse the rules the programme already carries, so no form has to be shown.
 */
export function useArrangeProgram(
  programId: string,
): UseMutationResult<Program, ApiError, ArrangeProgramInput | undefined> {
  return useProgramMutation<ArrangeProgramInput | undefined>(programId, (input) =>
    request<Envelope<Program>>(`staff/programs/${programId}/items/arrange`, {
      method: "post",
      json: input ?? {},
    }),
  );
}

/** Insert a break (or any other standalone block). */
export function useAddBlock(
  programId: string,
): UseMutationResult<Program, ApiError, AddBlockInput> {
  return useProgramMutation<AddBlockInput>(programId, (input) =>
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
  return useProgramMutation(programId, ({ itemId, ...body }) =>
    request<Envelope<Program>>(`staff/programs/${programId}/items/${itemId}`, {
      method: "patch",
      json: body,
    }),
  );
}

export function useRemoveItem(programId: string): UseMutationResult<Program, ApiError, string> {
  return useProgramMutation<string>(programId, (itemId) =>
    request<Envelope<Program>>(`staff/programs/${programId}/items/${itemId}`, {
      method: "delete",
    }),
  );
}

/** Send the complete new running order. Permanent numbers stay with their slots. */
export function useReorderItems(programId: string): UseMutationResult<Program, ApiError, string[]> {
  return useProgramMutation<string[]>(programId, (itemIds) =>
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
  return useProgramMutation<void>(programId, () =>
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

/** Add a column of the organizer's own to the programme's table. */
export function useAddColumn(programId: string): UseMutationResult<Program, ApiError, string> {
  return useProgramMutation<string>(programId, (title) =>
    request<Envelope<Program>>(`staff/programs/${programId}/columns`, {
      method: "post",
      json: { title },
    }),
  );
}

/** Rename a custom column. Its id — and so every value in it — is untouched. */
export function useRenameColumn(
  programId: string,
): UseMutationResult<Program, ApiError, { columnId: string; title: string }> {
  return useProgramMutation<{ columnId: string; title: string }>(programId, ({ columnId, title }) =>
    request<Envelope<Program>>(`staff/programs/${programId}/columns/${columnId}`, {
      method: "patch",
      json: { title },
    }),
  );
}

/** Remove a custom column, its values, and its place on every published link. */
export function useRemoveColumn(programId: string): UseMutationResult<Program, ApiError, string> {
  return useProgramMutation<string>(programId, (columnId) =>
    request<Envelope<Program>>(`staff/programs/${programId}/columns/${columnId}`, {
      method: "delete",
    }),
  );
}

/** Write the hand-filled cells of one row. A blank value clears one. */
export function useFillCells(
  programId: string,
): UseMutationResult<Program, ApiError, { itemId: string; values: Record<string, string> }> {
  return useProgramMutation<{ itemId: string; values: Record<string, string> }>(
    programId,
    ({ itemId, values }) =>
      request<Envelope<Program>>(`staff/programs/${programId}/items/${itemId}/cells`, {
        method: "put",
        json: { values },
      }),
  );
}

/**
 * Download the programme as a PDF table of the chosen columns.
 *
 * Fetched rather than linked: the endpoint is staff-gated, so the request needs the same
 * auth as everything else and a plain `<a href>` would arrive without it. The blob is then
 * handed to the browser under the filename the server chose.
 */
export async function downloadProgramPdf(
  programId: string,
  columns: ColumnKey[],
  fallbackName: string,
): Promise<void> {
  const query = columns.length > 0 ? `?columns=${encodeURIComponent(columns.join(","))}` : "";
  await saveAuthenticatedDownload(
    `staff/programs/${programId}/export.pdf${query}`,
    `${fallbackName}.pdf`,
  );
}

/**
 * Download the programme as one flat .xlsx sheet of the chosen columns.
 *
 * The same table as the PDF and the same column choice, in the format the programme is
 * actually worked in: sorted, filtered, pasted into somebody else's template. Written
 * сплошником — every slot one row, in running order, nothing merged or grouped.
 */
export async function downloadProgramXlsx(
  programId: string,
  columns: ColumnKey[],
  fallbackName: string,
): Promise<void> {
  const query = columns.length > 0 ? `?columns=${encodeURIComponent(columns.join(","))}` : "";
  await saveAuthenticatedDownload(
    `staff/programs/${programId}/export.xlsx${query}`,
    `${fallbackName}.xlsx`,
  );
}

/**
 * Download every backing track of the programme as one ZIP, named by number.
 *
 * What the sound desk is handed on the day. The archive is assembled per request from
 * the files the applicants already uploaded, so it can never be out of date with the
 * running order it was downloaded from.
 */
export async function downloadProgramMusic(programId: string, fallbackName: string): Promise<void> {
  await saveAuthenticatedDownload(
    `staff/programs/${programId}/music.zip`,
    `${fallbackName} — фонограммы.zip`,
  );
}

/**
 * Download every video and photograph of the programme as one ZIP, named by number.
 *
 * The screen operator's counterpart to the music archive, and a separate download for the
 * same reason the desks are separate: neither should have to search through the other's
 * material. Assembled per request, so it can never be out of date with the running order.
 */
export async function downloadProgramMedia(programId: string, fallbackName: string): Promise<void> {
  await saveAuthenticatedDownload(
    `staff/programs/${programId}/media.zip`,
    `${fallbackName} — медиафайлы.zip`,
  );
}

/** Put every slot back to pending — the organizer's reset after a rehearsal. */
export function useResetProgress(programId: string): UseMutationResult<Program, ApiError, void> {
  return useProgramMutation<void>(programId, () =>
    request<Envelope<Program>>(`staff/programs/${programId}/progress`, { method: "delete" }),
  );
}

/** Change which columns a live link shows (or rename it) — its slug is permanent. */
export function useUpdateShare(
  programId: string,
): UseMutationResult<
  ProgramShare,
  ApiError,
  { shareId: string; name?: string; columns?: ColumnKey[]; controlsRunningOrder?: boolean }
> {
  const queryClient = useQueryClient();
  return useMutation<
    ProgramShare,
    ApiError,
    { shareId: string; name?: string; columns?: ColumnKey[]; controlsRunningOrder?: boolean }
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

/**
 * Write to everyone this edition covers: the programme is up, here it is.
 *
 * Not a {@link useProgramMutation}: it changes nothing about the programme, so there is
 * no new state to write into the cache and nothing to serialize it against. What comes
 * back is a count of what was sent, which the caller reports and forgets.
 */
export function useAnnounceShare(
  programId: string,
): UseMutationResult<ProgramAnnouncement, ApiError, AnnounceShareInput> {
  return useMutation<ProgramAnnouncement, ApiError, AnnounceShareInput>({
    mutationFn: async ({ shareId, note }) =>
      (
        await request<Envelope<ProgramAnnouncement>>(
          `staff/programs/${programId}/shares/${shareId}/announce`,
          { method: "post", json: note ? { note } : {} },
        )
      ).data,
  });
}

/** Revoke an edition — its link stops resolving at once. */
export function useRemoveShare(programId: string): UseMutationResult<Program, ApiError, string> {
  return useProgramMutation<string>(programId, (shareId) =>
    request<Envelope<Program>>(`staff/programs/${programId}/shares/${shareId}`, {
      method: "delete",
    }),
  );
}
