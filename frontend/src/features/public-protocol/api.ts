/**
 * Data access for a published protocol and a competition's list of them (anyone-facing).
 *
 * Deliberately separate from `jury-protocols`: this reads two unauthenticated endpoints and
 * knows nothing about protocol ids, rows or awarding. Kept apart so an organizer-only field
 * — an applicant's email, a row's submission id — can never drift onto the public page.
 *
 * Nothing here polls. A published protocol changes when somebody deliberately publishes a
 * correction, which is a human act minutes or days apart, so the page is read once and the
 * backend's short `Cache-Control` does the rest. That is the whole difference from the
 * programme screen, which is live because a host is driving it in front of an audience.
 */
import { type UseQueryResult, useQuery } from "@tanstack/react-query";

import { type ApiError, apiClient, toApiError } from "@/shared/api";

/** One published column: its stable key and the header it is printed under. */
export interface PublicProtocolColumn {
  key: string;
  label: string;
}

/**
 * One row of the published table. `cells` is aligned with the protocol's `columns`.
 *
 * There is no field-by-field shape here on purpose: the backend renders only the published
 * columns into cells, so a column the organizer left out does not exist in this payload at
 * all and cannot be recovered from it. `award` is carried for styling only — Гран-при is
 * drawn differently — and the wording itself is already in `cells`.
 */
export interface PublicProtocolRow {
  cells: string[];
  award: string | null;
}

/** What a published protocol link resolves to. */
export interface PublicProtocol {
  name: string;
  slug: string;
  competitionTitle: string | null;
  nomination: string | null;
  /** Which publication of these results this is — 2 and up means a correction. */
  revision: number;
  publishedAt: string | null;
  columns: PublicProtocolColumn[];
  rows: PublicProtocolRow[];
}

/** One entry of a competition's "Результаты" section. */
export interface PublishedProtocolLink {
  nomination: string | null;
  name: string;
  slug: string;
  /** The client-side path this protocol lives at. */
  path: string;
  revision: number;
  publishedAt: string | null;
}

export const publicProtocolKeys = {
  detail: (slug: string) => ["public-protocol", slug] as const,
  competitionResults: (competitionId: string) => ["public-results", competitionId] as const,
};

interface Envelope<T> {
  data: T;
  meta?: { total?: number; requestId?: string };
}

export async function fetchPublicProtocol(slug: string): Promise<PublicProtocol> {
  try {
    const body = await apiClient(`public/protocols/${slug}`).json<Envelope<PublicProtocol>>();
    return body.data;
  } catch (error) {
    throw await toApiError(error);
  }
}

export async function fetchCompetitionResults(
  competitionId: string,
): Promise<PublishedProtocolLink[]> {
  try {
    const body = await apiClient(`public/competitions/${competitionId}/results`).json<
      Envelope<PublishedProtocolLink[]>
    >();
    return body.data;
  } catch (error) {
    throw await toApiError(error);
  }
}

export function usePublicProtocol(
  slug: string | undefined,
): UseQueryResult<PublicProtocol, ApiError> {
  return useQuery<PublicProtocol, ApiError>({
    enabled: Boolean(slug),
    queryKey: publicProtocolKeys.detail(slug ?? ""),
    queryFn: () => fetchPublicProtocol(slug ?? ""),
    // A results page is a document: read it once and keep it for the visit.
    staleTime: 60_000,
    retry: false,
  });
}

/**
 * The protocols a competition has published.
 *
 * Answers an empty list rather than an error for a competition that has published nothing,
 * which is what lets the landing page hide the section entirely instead of showing an empty
 * heading — and why a failure here is not worth retrying either.
 */
export function useCompetitionResults(
  competitionId: string | undefined,
): UseQueryResult<PublishedProtocolLink[], ApiError> {
  return useQuery<PublishedProtocolLink[], ApiError>({
    enabled: Boolean(competitionId),
    queryKey: publicProtocolKeys.competitionResults(competitionId ?? ""),
    queryFn: () => fetchCompetitionResults(competitionId ?? ""),
    staleTime: 60_000,
    retry: false,
  });
}
