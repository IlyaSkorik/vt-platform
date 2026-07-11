import type { CompetitionSummary } from "@/shared/api/generated/model-competitions";
import { createUuidV7, isUuidV7 } from "@/shared/lib/uuid";

const STORAGE_KEY = "vt:organizer-id";

/** Persist the organization id for subsequent competition creation. */
export function cacheOrganizerId(organizerId: string): void {
  if (!isUuidV7(organizerId)) {
    return;
  }
  try {
    sessionStorage.setItem(STORAGE_KEY, organizerId);
  } catch {
    // sessionStorage may be unavailable in non-browser environments.
  }
}

function readCachedOrganizerId(): string | null {
  try {
    const cached = sessionStorage.getItem(STORAGE_KEY);
    if (cached && isUuidV7(cached)) {
      return cached;
    }
    if (cached) {
      sessionStorage.removeItem(STORAGE_KEY);
    }
    return null;
  } catch {
    return null;
  }
}

function createSessionOrganizerId(): string {
  const generated = createUuidV7();
  cacheOrganizerId(generated);
  return generated;
}

/**
 * Resolve the organizer id from existing competitions, session storage, or a
 * session-scoped UUID v7 fallback. Backend OrganizerId rejects anything but UUID v7.
 */
export function resolveOrganizerId(competitions: readonly CompetitionSummary[]): string {
  const fromList = competitions.find((item) => isUuidV7(item.organizerId))?.organizerId;
  if (fromList) {
    cacheOrganizerId(fromList);
    return fromList;
  }

  const cached = readCachedOrganizerId();
  if (cached) {
    return cached;
  }

  return createSessionOrganizerId();
}
