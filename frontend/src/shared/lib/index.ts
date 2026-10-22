/** Public API of the `shared/lib` segment. */
export { cn } from "./cn";
export { isExternalDocLink, isGoogleDocsUrl, toEmbeddableDocUrl } from "./doc-embed";
export { formatClock, formatDuration, formatSpan } from "./duration";
export { festivalPath, festivalSegment } from "./festival-address";
export {
  FESTIVAL_TIME_ZONE,
  festivalInputToIso,
  isoToFestivalInput,
} from "./festival-time";
export { resolveMediaUrl } from "./media";
export { formatPersonName } from "./person-name";
export {
  authPathWithNext,
  clearPostAuthRedirect,
  isSafeRedirect,
  readPostAuthRedirect,
  rememberPostAuthRedirect,
} from "./post-auth-redirect";
export { createUuidV7, isUuidV7, timestampFromUuidV7 } from "./uuid";
export { z } from "./zod";
