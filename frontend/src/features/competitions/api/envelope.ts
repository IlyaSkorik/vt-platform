import type {
  CompetitionDetail,
  CompetitionSummary,
} from "@/shared/api/generated/model-competitions";

/** Wire envelope returned by competition list endpoints. */
export interface CompetitionListEnvelope {
  data: CompetitionSummary[];
  meta?: { requestId?: string };
}

/** Wire envelope returned by competition detail endpoints. */
export interface CompetitionDetailEnvelope {
  data: CompetitionDetail;
  meta?: { requestId?: string };
}

/** Unwrap a list response body from the Orval `{ status, data }` envelope. */
export function unwrapCompetitionList(body: unknown): CompetitionSummary[] {
  if (body != null && typeof body === "object" && "data" in body) {
    const nested = (body as CompetitionListEnvelope).data;
    if (Array.isArray(nested)) {
      return nested;
    }
  }
  return [];
}

/** Unwrap a detail response body from the Orval `{ status, data }` envelope. */
export function unwrapCompetitionDetail(body: unknown): CompetitionDetail {
  if (body != null && typeof body === "object" && "data" in body) {
    const nested = (body as CompetitionDetailEnvelope).data;
    if (nested != null && typeof nested === "object" && "id" in nested) {
      return nested;
    }
  }
  throw new Error("Unexpected competition detail response.");
}
