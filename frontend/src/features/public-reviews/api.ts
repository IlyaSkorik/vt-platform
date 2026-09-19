/**
 * Data access for the review form (anyone-facing).
 *
 * Deliberately separate from `reviews-console`: this reads one unauthenticated
 * endpoint by slug and knows nothing about review ids, the organizer's settings or
 * what has already been left. Kept apart so an organizer-only field can never
 * drift onto a page anybody with a phone can open.
 *
 * Everything travels in one multipart request — words, name, festival, consent and
 * photographs together — because a photograph uploaded ahead of a note that is
 * then abandoned is a file the platform holds for no reason.
 */
import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
} from "@tanstack/react-query";

import { type ApiError, apiClient, toApiError, uploadTimeoutMs } from "@/shared/api";

/** One festival the note may be filed under. Naming none is the ordinary case. */
export interface ReviewFestivalOption {
  id: string;
  title: string;
}

/** What a review link resolves to. */
export interface PublicReviewPage {
  slug: string;
  title: string;
  intro: string;
  organizationName: string;
  /**
   * Whether a note sent right now would be kept.
   *
   * A closed page still resolves: the banner is printed and will outlive the
   * season, so the link explains itself rather than 404ing at somebody who walked
   * over to it.
   */
  accepting: boolean;
  festivals: ReviewFestivalOption[];
}

/** The note as it comes back, once it has been accepted. */
export interface SubmittedReview {
  id: string;
  authorName: string | null;
  text: string;
  photos: string[];
  competitionId: string | null;
  competitionTitle: string | null;
  submittedAt: string;
}

export interface ReviewDraft {
  text: string;
  /** Left empty by most people. An unsigned note is a whole note. */
  authorName: string;
  competitionId: string | null;
  photos: File[];
  consentType: string;
  consentVersion: string;
}

export const publicReviewKeys = {
  page: (slug: string) => ["public-review-page", slug] as const,
};

export async function fetchPublicReviewPage(
  slug: string,
  signal?: AbortSignal,
): Promise<PublicReviewPage> {
  try {
    const body = await apiClient(`public/reviews/${encodeURIComponent(slug)}`, {
      ...(signal ? { signal } : {}),
    }).json<{ data: PublicReviewPage }>();
    return body.data;
  } catch (error) {
    throw await toApiError(error);
  }
}

/** The page behind a scanned code. */
export function usePublicReviewPage(
  slug: string | undefined,
): UseQueryResult<PublicReviewPage, ApiError> {
  return useQuery<PublicReviewPage, ApiError>({
    enabled: Boolean(slug),
    queryKey: publicReviewKeys.page(slug ?? ""),
    queryFn: ({ signal }) => fetchPublicReviewPage(slug ?? "", signal),
    retry: false,
  });
}

/**
 * Leave a review.
 *
 * `consentAccepted` is sent as an explicit `true` rather than implied by the
 * request existing: the server refuses without it, and a payload that states it
 * is a payload that can be read back later as evidence of what was asked.
 */
export function useSubmitReview(
  slug: string,
): UseMutationResult<SubmittedReview, ApiError, ReviewDraft> {
  return useMutation<SubmittedReview, ApiError, ReviewDraft>({
    mutationFn: async (draft) => {
      const body = new FormData();
      body.append("text", draft.text);
      body.append("consentType", draft.consentType);
      body.append("consentVersion", draft.consentVersion);
      body.append("consentAccepted", "true");
      if (draft.authorName.trim()) {
        body.append("authorName", draft.authorName.trim());
      }
      if (draft.competitionId) {
        body.append("competitionId", draft.competitionId);
      }
      for (const photo of draft.photos) {
        body.append("photos", photo);
      }
      try {
        const response = await apiClient(`public/reviews/${encodeURIComponent(slug)}/entries`, {
          method: "post",
          body,
          // Photographs from a phone over a hall's wifi: the default timeout is for
          // JSON, and cutting a working upload off is worse than waiting for it.
          timeout: uploadTimeoutMs(body),
        }).json<{ data: SubmittedReview }>();
        return response.data;
      } catch (error) {
        throw await toApiError(error);
      }
    },
  });
}
