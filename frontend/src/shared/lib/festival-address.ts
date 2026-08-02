/**
 * How a competition is addressed in a URL.
 *
 * The readable slug when the backend has one, the uuid otherwise. Kept in one
 * place because every surface that links a festival — the catalog card, the
 * featured panel, the home page, the sitemap's counterpart on the server — has
 * to make the same choice; two of them disagreeing would mean the same festival
 * indexed twice under different addresses, which search treats as duplicate
 * content and resolves by picking one arbitrarily.
 */

/** Just the identifying part: what goes after `/competitions/`. */
export function festivalSegment(festival: { id: string; slug?: string | null }): string {
  return festival.slug?.trim() || festival.id;
}

/** The full path to a competition under `basePath`. */
export function festivalPath(
  festival: { id: string; slug?: string | null },
  basePath: string,
): string {
  return `${basePath}/${festivalSegment(festival)}`;
}
