/** Public API of the reviews console (organizer's workspace and operator's). */

export {
  type Review,
  type ReviewPage,
  reviewKeys,
  type UpdateReviewPageInput,
  useDeleteReview,
  usePlatformReviews,
  useReviewPage,
  useReviews,
  useUpdateReviewPage,
} from "./api";
export { authorLabel, OPEN_LINK_NOTE, publicReviewUrl } from "./model";
