/** TanStack Query keys for the participant's documents. */
export const myDocumentsKeys = {
  all: ["my-documents"] as const,
  list: () => [...myDocumentsKeys.all, "list"] as const,
};
