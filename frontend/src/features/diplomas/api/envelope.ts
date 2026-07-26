import type {
  AssignmentResponse,
  DiplomaResponse,
  GenerateDocumentsResponse,
  LayoutResponse,
  PreviewApplication,
  PreviewBindings,
  PrintJobResponse,
  PrintPackageSummaryResponse,
  TemplateResponse,
} from "@/shared/api/generated/model-diplomas";

/**
 * The backend wraps every payload in a `{ data, meta }` envelope, while the
 * Orval `fetch` client already wraps the HTTP body in its own `{ status, data }`
 * shape. So the response body handed to these helpers is the platform envelope;
 * we unwrap its inner `data`.
 */
function unwrapList<T>(body: unknown): T[] {
  if (body != null && typeof body === "object" && "data" in body) {
    const nested = (body as { data: unknown }).data;
    if (Array.isArray(nested)) {
      return nested as T[];
    }
  }
  return [];
}

function unwrapItem<T>(body: unknown): T {
  if (body != null && typeof body === "object" && "data" in body) {
    const nested = (body as { data: unknown }).data;
    if (nested != null && typeof nested === "object") {
      return nested as T;
    }
  }
  throw new Error("Unexpected diploma response.");
}

export const unwrapTemplateList = (body: unknown): TemplateResponse[] =>
  unwrapList<TemplateResponse>(body);

export const unwrapAssignmentList = (body: unknown): AssignmentResponse[] =>
  unwrapList<AssignmentResponse>(body);

export const unwrapAssignment = (body: unknown): AssignmentResponse =>
  unwrapItem<AssignmentResponse>(body);

export const unwrapLayout = (body: unknown): LayoutResponse => unwrapItem<LayoutResponse>(body);

export const unwrapPreviewApplications = (body: unknown): PreviewApplication[] =>
  unwrapList<PreviewApplication>(body);

export const unwrapPreviewBindings = (body: unknown): Record<string, string> =>
  unwrapItem<PreviewBindings>(body).bindings;

export const unwrapDiplomaList = (body: unknown): DiplomaResponse[] =>
  unwrapList<DiplomaResponse>(body);

export const unwrapPrintJob = (body: unknown): PrintJobResponse =>
  unwrapItem<PrintJobResponse>(body);

export const unwrapPrintSummary = (body: unknown): PrintPackageSummaryResponse =>
  unwrapItem<PrintPackageSummaryResponse>(body);

export const unwrapGeneratedDocuments = (body: unknown): GenerateDocumentsResponse =>
  unwrapItem<GenerateDocumentsResponse>(body);
