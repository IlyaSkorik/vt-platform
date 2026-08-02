import { useEffect } from "react";
import { useLocation } from "react-router";
import { APP_NAME, env } from "@/shared/config";
import { SEO_PRIORITY, type SeoDescriptor, writeDocumentHead } from "./document-head";

/** What a page passes in: the descriptor, minus the parts we can derive. */
export interface SeoInput extends Omit<SeoDescriptor, "canonical"> {
  /**
   * Path this page should be canonical at, absolute-from-root and without a
   * query string. Defaults to the current pathname, which is right for every
   * page whose URL is already its identity; pass it explicitly where several
   * URLs render the same thing.
   */
  canonicalPath?: string | undefined;
  /** Omit the canonical entirely — for pages that must never be a search result. */
  noCanonical?: boolean | undefined;
}

/** Turn a root-relative path into the absolute URL crawlers require. */
export function absoluteUrl(path: string): string {
  return `${env.siteUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

function useSeoAt(input: SeoInput, priority: number): void {
  const { pathname } = useLocation();
  const canonicalPath = input.canonicalPath ?? pathname;
  // A page that refuses indexing gets no canonical either: pointing a crawler at
  // a URL and telling it to stay away are contradictory instructions, and the
  // one that survives is whichever the crawler feels like honouring.
  const canonical =
    input.noCanonical || input.robots === "noindex" ? undefined : absoluteUrl(canonicalPath);

  const { title, standaloneTitle, description, image, imageAlt, type, robots } = input;

  useEffect(() => {
    writeDocumentHead(
      { title, standaloneTitle, description, canonical, image, imageAlt, type, robots },
      { location: pathname, priority, siteName: APP_NAME },
    );
  }, [
    title,
    standaloneTitle,
    description,
    canonical,
    image,
    imageAlt,
    type,
    robots,
    pathname,
    priority,
  ]);
}

/**
 * Declare a page's title, description and sharing preview.
 *
 * Call this once per route element. The write lands in the document head
 * immediately and is superseded on the next navigation, so a page never has to
 * clean up after itself.
 */
export function useSeo(input: SeoInput): void {
  useSeoAt(input, SEO_PRIORITY.page);
}

/**
 * The same, but yielding to any page that declares its own.
 *
 * Layouts use this to give a whole section a floor — most importantly the
 * ``noindex`` that keeps the cabinet, the staff panel and the operator console
 * out of search results without every one of their ~58 routes having to
 * remember. A new private page is closed by the layout it is added under, not
 * by the diligence of whoever adds it.
 */
export function useSectionSeo(input: SeoInput): void {
  useSeoAt(input, SEO_PRIORITY.layout);
}
