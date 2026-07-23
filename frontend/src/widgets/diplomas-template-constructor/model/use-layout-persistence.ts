import { type TemplateField, useSaveTemplateLayoutMutation } from "@/features/diplomas";
import type { ApiError } from "@/shared/api";

export interface LayoutPersistence {
  /** Persist the whole layout in one atomic request. */
  save: (fields: TemplateField[]) => Promise<void>;
  isSaving: boolean;
  error: ApiError | null;
}

/**
 * PersistenceService: the seam between the editor's in-memory state and the
 * network. It knows how to persist a layout (whole-document, atomic) but owns no
 * editor state — the caller passes the current fields and reacts to the result.
 */
export function useLayoutPersistence(templateId: string): LayoutPersistence {
  const mutation = useSaveTemplateLayoutMutation();
  return {
    save: async (fields) => {
      await mutation.mutateAsync({ templateId, fields });
    },
    isSaving: mutation.isPending,
    error: mutation.error,
  };
}
