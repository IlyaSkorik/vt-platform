/**
 * Data access for the diploma font library.
 *
 * Hand-written rather than generated, like the programme constructor's client: the catalog is
 * a small, stable shape and the upload is `multipart/form-data`, which the generated fetch
 * client does not model well.
 *
 * Both writes answer with the whole catalog, so the dropdown and the library screen are
 * refreshed from the response of the action that changed them — an uploaded family is
 * selectable immediately, without a second request.
 */
import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { type ApiError, apiClient, toApiError } from "@/shared/api";

import type { FontCatalog } from "../model/fonts";
import { diplomaKeys } from "./keys";

interface Envelope<T> {
  data: T;
  meta?: { requestId?: string };
}

const EMPTY_CATALOG: FontCatalog = { families: [], uploaded: [] };

export const fontKeys = {
  catalog: () => [...diplomaKeys.all, "fonts"] as const,
};

export async function fetchFontCatalog(): Promise<FontCatalog> {
  try {
    const body = await apiClient("staff/diplomas/fonts").json<Envelope<FontCatalog>>();
    return body.data;
  } catch (error) {
    throw await toApiError(error);
  }
}

/**
 * The font catalog.
 *
 * Cached for the session: the list changes only when somebody uploads or deletes a font, and
 * both of those write the fresh catalog straight into this cache.
 */
export function useFontCatalog(): UseQueryResult<FontCatalog, ApiError> {
  return useQuery<FontCatalog, ApiError>({
    queryKey: fontKeys.catalog(),
    queryFn: fetchFontCatalog,
    staleTime: 5 * 60_000,
    // The constructor must still open when the catalog cannot be read — it falls back to the
    // families a template already names, which the renderer resolves on its own.
    retry: false,
  });
}

/** The catalog, or an empty one — for callers that only need to render a list. */
export function useFontCatalogData(): FontCatalog {
  return useFontCatalog().data ?? EMPTY_CATALOG;
}

export function useUploadFont(): UseMutationResult<FontCatalog, ApiError, File> {
  const queryClient = useQueryClient();
  return useMutation<FontCatalog, ApiError, File>({
    mutationFn: async (file) => {
      const body = new FormData();
      body.append("file", file);
      try {
        // No explicit Content-Type: the boundary is part of it, so the browser must set it.
        const response = await apiClient("staff/diplomas/fonts", { method: "post", body }).json<
          Envelope<FontCatalog>
        >();
        return response.data;
      } catch (error) {
        throw await toApiError(error);
      }
    },
    onSuccess: (catalog) => {
      queryClient.setQueryData(fontKeys.catalog(), catalog);
    },
  });
}

export function useDeleteFont(): UseMutationResult<void, ApiError, string> {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, string>({
    mutationFn: async (fontId) => {
      try {
        // 204 No Content: nothing to parse.
        await apiClient(`staff/diplomas/fonts/${fontId}`, { method: "delete" });
      } catch (error) {
        throw await toApiError(error);
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: fontKeys.catalog() });
    },
  });
}
