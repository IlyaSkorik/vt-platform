/** Query keys for the cabinet notification feed. */
export const notificationKeys = {
  all: ["notifications"] as const,
  feed: (limit: number) => ["notifications", "feed", limit] as const,
};
