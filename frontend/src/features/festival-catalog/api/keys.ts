/** TanStack Query keys for the public festival catalog. */
export const festivalCatalogKeys = {
  all: ["festival-catalog"] as const,
  list: () => [...festivalCatalogKeys.all, "list"] as const,
};
