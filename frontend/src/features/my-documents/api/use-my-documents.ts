import { type UseQueryResult, useQuery } from "@tanstack/react-query";
import { type ApiError, toApiError } from "@/shared/api";
import type { ParticipantDocumentsEnvelope } from "@/shared/api/generated/model-my-documents";
import { listMyDocuments } from "@/shared/api/generated/my-documents/my-documents";
import type { MyDocument } from "../lib/types";
import { myDocumentsKeys } from "./keys";

/** Unwrap the `{ data, meta }` envelope into the document list. */
function unwrapDocuments(body: unknown): MyDocument[] {
  if (body != null && typeof body === "object" && "data" in body) {
    const nested = (body as ParticipantDocumentsEnvelope).data;
    if (Array.isArray(nested)) {
      return nested;
    }
  }
  throw new Error("Не удалось загрузить ваши документы. Попробуйте ещё раз.");
}

async function fetchMyDocuments(signal?: AbortSignal): Promise<MyDocument[]> {
  try {
    const response = await listMyDocuments(signal ? { signal } : {});
    return unwrapDocuments(response.data);
  } catch (error) {
    throw await toApiError(error);
  }
}

/**
 * The authenticated participant's issued documents.
 *
 * Scoped server-side to the caller, so there is no id to pass. Kept fresh for a
 * minute: a document can appear without any action by this user — a thank-you
 * letter publishes the moment the organizer generates it — so the cabinet should
 * not hold a stale empty list for long.
 */
export function useMyDocuments(): UseQueryResult<MyDocument[], ApiError> {
  return useQuery<MyDocument[], ApiError>({
    queryKey: myDocumentsKeys.list(),
    queryFn: ({ signal }) => fetchMyDocuments(signal),
    staleTime: 60_000,
  });
}
