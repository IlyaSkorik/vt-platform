/** TanStack Query keys for competition resources. */
export const competitionKeys = {
  all: ["competitions"] as const,
  lists: () => [...competitionKeys.all, "list"] as const,
  list: () => [...competitionKeys.lists()] as const,
  details: () => [...competitionKeys.all, "detail"] as const,
  detail: (competitionId: string) => [...competitionKeys.details(), competitionId] as const,
};
