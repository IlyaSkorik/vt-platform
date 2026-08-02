/**
 * The single writer that owns the document's SEO-relevant `<head>`.
 *
 * Every tag here is written *imperatively* rather than rendered through React's
 * own `<title>`/`<meta>` hoisting. React appends the tags it hoists, so a static
 * `<title>` in `index.html` — or, later, a server-injected one — would sit
 * alongside the React one and win, since the browser honours the first. Writing
 * in place means one tag per fact no matter who put it there first, which is
 * exactly what the head-rendering step will need when the public routes start
 * being served with their meta already filled in.
 */

/**
 * The head facts a page can declare. Everything is optional but `title`.
 *
 * Each optional field spells out `| undefined` because the project compiles with
 * `exactOptionalPropertyTypes`: callers build these descriptors from data that is
 * genuinely absent — a festival with no poster — and "absent" has to be sayable
 * without the caller stripping the key by hand.
 */
export interface SeoDescriptor {
  /** The page's own name, composed with the site name unless `standaloneTitle`. */
  title: string;
  /** Use `title` verbatim, without the " — Взлёт талантов" suffix. */
  standaloneTitle?: boolean | undefined;
  description?: string | undefined;
  /** Absolute canonical URL. Omitted tags are removed, never left stale. */
  canonical?: string | undefined;
  /** Absolute URL of the sharing preview image. */
  image?: string | undefined;
  /** Alt text for the preview image; screen readers on social networks use it. */
  imageAlt?: string | undefined;
  /** Open Graph object type. `website` for listings, `article` for prose. */
  type?: "website" | "article" | undefined;
  /** Whether search engines may index this page. Defaults to indexable. */
  robots?: "index" | "noindex" | undefined;
}

/** Tags this module manages, marked so it never disturbs anything else. */
const OWNED = "data-seo";

/**
 * The write that wins for the current page.
 *
 * Effects run child-first, so a page's descriptor is applied *before* the
 * layout's fallback. Priorities let the later, coarser write stand down instead
 * of clobbering the more specific one; the pair resets whenever the location
 * changes, so the next page starts from a clean contest.
 */
let currentLocation = "";
let currentPriority = -1;
/**
 * Whether anything has refused indexing for this location.
 *
 * Recorded separately from the winning write, and never cleared within a
 * location, because refusing to be indexed is a safety property: a page that
 * declares a nicer title inside the cabinet must not silently re-open the
 * cabinet to crawlers just because it forgot to repeat the refusal. The
 * restrictive answer wins regardless of who is more specific.
 */
let currentNoindex = false;

/** Priority levels — higher wins for the same location. */
export const SEO_PRIORITY = { layout: 0, page: 1 } as const;

function upsertMeta(
  selector: string,
  attribute: "name" | "property",
  key: string,
  content: string | undefined,
): void {
  const existing = document.head.querySelector<HTMLMetaElement>(selector);
  if (content === undefined || content === "") {
    // Only ours is removed: a tag written by the server or by index.html and
    // never claimed here is not this module's to delete.
    if (existing?.hasAttribute(OWNED)) existing.remove();
    return;
  }
  const tag = existing ?? document.head.appendChild(document.createElement("meta"));
  tag.setAttribute(attribute, key);
  tag.setAttribute(OWNED, "");
  tag.setAttribute("content", content);
}

function upsertLink(rel: string, href: string | undefined): void {
  const existing = document.head.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`);
  if (href === undefined || href === "") {
    if (existing?.hasAttribute(OWNED)) existing.remove();
    return;
  }
  const tag = existing ?? document.head.appendChild(document.createElement("link"));
  tag.setAttribute("rel", rel);
  tag.setAttribute(OWNED, "");
  tag.setAttribute("href", href);
}

/**
 * Absent means indexable: that is the crawler's default, and stating it adds a
 * tag that says nothing. Only the refusal is worth writing down.
 */
function applyRobots(noindex: boolean): void {
  upsertMeta('meta[name="robots"]', "name", "robots", noindex ? "noindex, nofollow" : undefined);
}

/**
 * Project `seo` onto the document head, unless a higher-priority write already
 * claimed this location. Returns whether the write was applied.
 */
export function writeDocumentHead(
  seo: SeoDescriptor,
  { location, priority, siteName }: { location: string; priority: number; siteName: string },
): boolean {
  if (location !== currentLocation) {
    currentLocation = location;
    currentPriority = -1;
    currentNoindex = false;
  }
  // Noted before the priority check: a layout's refusal arrives *after* the
  // page's write (effects run child-first) and would otherwise be dropped as
  // the losing bid.
  if (seo.robots === "noindex") currentNoindex = true;

  if (priority < currentPriority) {
    // The losing write still gets to tighten robots if it just did.
    if (currentNoindex) applyRobots(true);
    return false;
  }
  currentPriority = priority;

  const title = seo.standaloneTitle ? seo.title : `${seo.title} — ${siteName}`;
  document.title = title;

  upsertMeta('meta[name="description"]', "name", "description", seo.description);
  applyRobots(currentNoindex);
  upsertLink("canonical", currentNoindex ? undefined : seo.canonical);

  upsertMeta('meta[property="og:title"]', "property", "og:title", title);
  upsertMeta('meta[property="og:description"]', "property", "og:description", seo.description);
  upsertMeta('meta[property="og:type"]', "property", "og:type", seo.type ?? "website");
  upsertMeta('meta[property="og:url"]', "property", "og:url", seo.canonical);
  upsertMeta('meta[property="og:site_name"]', "property", "og:site_name", siteName);
  upsertMeta('meta[property="og:locale"]', "property", "og:locale", "ru_RU");
  upsertMeta('meta[property="og:image"]', "property", "og:image", seo.image);
  upsertMeta(
    'meta[property="og:image:alt"]',
    "property",
    "og:image:alt",
    seo.image ? seo.imageAlt : undefined,
  );

  // Twitter reads most of Open Graph, but not the card kind — and without a card
  // kind it renders the bare link. The rest is left to og:* rather than doubled.
  upsertMeta(
    'meta[name="twitter:card"]',
    "name",
    "twitter:card",
    seo.image ? "summary_large_image" : "summary",
  );

  return true;
}

/** Reset the priority contest. For tests, which share one document. */
export function resetDocumentHeadState(): void {
  currentLocation = "";
  currentPriority = -1;
  currentNoindex = false;
}
