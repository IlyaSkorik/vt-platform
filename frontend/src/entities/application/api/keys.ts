/**
 * TanStack Query keys for the Application (order) domain.
 *
 * A single factory so every hook and every cache-invalidation call references the
 * same, well-typed keys — no stringly-typed drift.
 */
export const applicationKeys = {
  all: ["applications"] as const,
  lists: () => [...applicationKeys.all, "list"] as const,
  list: (status?: string) => [...applicationKeys.lists(), status ?? "all"] as const,
  details: () => [...applicationKeys.all, "detail"] as const,
  detail: (applicationId: string) => [...applicationKeys.details(), applicationId] as const,
  submissions: () => ["submissions"] as const,
  submission: (submissionId: string) => [...applicationKeys.submissions(), submissionId] as const,
};
