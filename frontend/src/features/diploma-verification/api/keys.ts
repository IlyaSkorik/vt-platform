/** TanStack Query keys for the public diploma authenticity page. */
export const diplomaVerificationKeys = {
  all: ["diploma-verification"] as const,
  byToken: (verificationToken: string) =>
    [...diplomaVerificationKeys.all, "token", verificationToken] as const,
};
