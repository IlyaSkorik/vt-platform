/** TanStack Query keys for the public competition landing page. */
export const festivalLandingKeys = {
  all: ["festival-landing"] as const,
  detail: (festivalId: string) => [...festivalLandingKeys.all, "detail", festivalId] as const,
};
