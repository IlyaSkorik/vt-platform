/**
 * Data access for the reviews an organization has collected.
 *
 * Two audiences, one shape. The organizer reads their own page and the notes left
 * on it; the platform operator reads every note on the platform, each labelled
 * with whose it is. They are separate endpoints with separate permissions, and
 * separate query keys — a cache shared between "mine" and "everyone's" is how an
 * operator's view ends up rendered in somebody's workspace.
 */
import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { type ApiError, apiClient, toApiError } from "@/shared/api";

/** The organization's review page, as its owner administers it. */
export interface ReviewPage {
  id: string;
  /** Permanent: it is printed on a banner. */
  slug: string;
  title: string;
  intro: string;
  /** Whether the link still takes notes. Off, it answers and says so. */
  accepting: boolean;
  reviewCount: number;
  createdAt: string;
  updatedAt: string;
}

/** One note, as the organizer (or the operator) reads it. */
export interface Review {
  id: string;
  authorName: string | null;
  text: string;
  /** Addresses, not storage keys — the server resolves them. */
  photos: string[];
  competitionId: string | null;
  competitionTitle: string | null;
  submittedAt: string;
  /** The wording its author accepted, kept with the note (LEGAL-001 §13.3). */
  consentType: string;
  consentVersion: string;
  consentAcceptedAt: string;
  organizationId: string;
  /** Filled only in the operator's console, which spans organizations. */
  organizationName: string | null;
}

export interface UpdateReviewPageInput {
  title?: string;
  intro?: string;
  accepting?: boolean;
}

export const reviewKeys = {
  page: ["review-page"] as const,
  list: ["reviews"] as const,
  platformList: ["platform-reviews"] as const,
};

async function unwrap<T>(promise: Promise<{ data: T }>): Promise<T> {
  try {
    return (await promise).data;
  } catch (error) {
    throw await toApiError(error);
  }
}

/**
 * The organization's page.
 *
 * Reading it is what creates it: the server mints the page on first sight, so the
 * link comes into existence once, before anybody prints it, rather than behind a
 * "create page" button whose only effect is to enable the button beside it.
 */
export function useReviewPage(): UseQueryResult<ReviewPage, ApiError> {
  return useQuery<ReviewPage, ApiError>({
    queryKey: reviewKeys.page,
    queryFn: () => unwrap(apiClient("staff/reviews/page").json<{ data: ReviewPage }>()),
  });
}

export function useUpdateReviewPage(): UseMutationResult<
  ReviewPage,
  ApiError,
  UpdateReviewPageInput
> {
  const queryClient = useQueryClient();
  return useMutation<ReviewPage, ApiError, UpdateReviewPageInput>({
    mutationFn: (input) =>
      unwrap(
        apiClient("staff/reviews/page", { method: "patch", json: input }).json<{
          data: ReviewPage;
        }>(),
      ),
    onSuccess: (page) => {
      queryClient.setQueryData(reviewKeys.page, page);
    },
  });
}

/** The notes left on this organization's page, newest first. */
export function useReviews(): UseQueryResult<Review[], ApiError> {
  return useQuery<Review[], ApiError>({
    queryKey: reviewKeys.list,
    queryFn: () => unwrap(apiClient("staff/reviews").json<{ data: Review[] }>()),
  });
}

/** Every note on the platform — the operator's read, and nobody else's. */
export function usePlatformReviews(): UseQueryResult<Review[], ApiError> {
  return useQuery<Review[], ApiError>({
    queryKey: reviewKeys.platformList,
    queryFn: () => unwrap(apiClient("platform/reviews").json<{ data: Review[] }>()),
  });
}

/**
 * Remove a note.
 *
 * `scope` decides which endpoint answers, not merely which list refreshes: the
 * operator may remove anybody's note and the organizer only their own, and that
 * distinction belongs on the wire rather than in this file's confidence.
 */
export function useDeleteReview(
  scope: "staff" | "platform" = "staff",
): UseMutationResult<void, ApiError, string> {
  const queryClient = useQueryClient();
  const base = scope === "platform" ? "platform/reviews" : "staff/reviews";
  return useMutation<void, ApiError, string>({
    mutationFn: async (reviewId) => {
      try {
        await apiClient(`${base}/${encodeURIComponent(reviewId)}`, { method: "delete" });
      } catch (error) {
        throw await toApiError(error);
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: reviewKeys.list });
      void queryClient.invalidateQueries({ queryKey: reviewKeys.platformList });
      // The count on the page card is part of what just changed.
      void queryClient.invalidateQueries({ queryKey: reviewKeys.page });
    },
  });
}
