import type {
  PublicFestival,
  PublicFestivalDetail,
} from "@/shared/api/generated/model-public-catalog";
import { APP_NAME } from "@/shared/config";
import { festivalPath, resolveMediaUrl } from "@/shared/lib";
import { absoluteUrl } from "./use-seo";

/**
 * schema.org graphs for the public pages.
 *
 * These are what let a competition appear in search as a dated event with a
 * place and a price rather than a blue link. Every builder omits a field it
 * cannot fill honestly: a half-populated `Event` is rejected wholesale by
 * validators, and inventing a date to satisfy one would put a wrong date in
 * front of a parent looking for the real one.
 */

/** Drop every key whose value is nullish, recursively, and empty objects with it. */
function compact<T extends Record<string, unknown>>(value: T): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, entry] of Object.entries(value)) {
    if (entry === null || entry === undefined || entry === "") continue;
    if (Array.isArray(entry) && entry.length === 0) continue;
    result[key] = entry;
  }
  return result;
}

/** The organization behind the site itself — not a festival's organizer. */
export function organizationSchema(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: APP_NAME,
    url: absoluteUrl("/"),
    description:
      "Цифровая платформа для организации и проведения детских творческих фестивалей и конкурсов.",
  };
}

/** The site as an entity, so search can attribute the name to the domain. */
export function webSiteSchema(): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: APP_NAME,
    url: absoluteUrl("/"),
    inLanguage: "ru-RU",
  };
}

/**
 * `IN_PERSON` / `ONLINE` / `HYBRID` as schema.org understands attendance.
 *
 * A competition reports every mode it runs in; schema.org allows exactly one, so
 * a festival offering both is `Mixed`.
 */
function attendanceMode(modes: readonly string[]): string | null {
  const online = modes.includes("ONLINE");
  const inPerson = modes.includes("IN_PERSON");
  if (modes.includes("HYBRID") || (online && inPerson)) {
    return "https://schema.org/MixedEventAttendanceMode";
  }
  if (online) return "https://schema.org/OnlineEventAttendanceMode";
  if (inPerson) return "https://schema.org/OfflineEventAttendanceMode";
  return null;
}

function place(festival: Pick<PublicFestival, "city" | "venueName" | "venueAddress">) {
  const address = festival.venueAddress ?? festival.city;
  if (!festival.venueName && !address) return null;
  return compact({
    "@type": "Place",
    name: festival.venueName ?? festival.city,
    address: address
      ? compact({
          "@type": "PostalAddress",
          streetAddress: festival.venueAddress,
          addressLocality: festival.city,
          addressCountry: "BY",
        })
      : null,
  });
}

function offers(
  festival: Pick<PublicFestival, "pricing" | "registrationStart">,
  { path }: { path: string },
) {
  const { amountFrom, currency } = festival.pricing;
  if (!amountFrom) return null;
  return compact({
    "@type": "Offer",
    // The catalog reports the cheapest entry across nominations, so this is a
    // floor. `lowPrice` on an AggregateOffer would say so more precisely, but it
    // requires a highPrice the projection does not carry — and a made-up ceiling
    // in front of a parent comparing festivals is worse than a plain "from".
    price: amountFrom,
    priceCurrency: currency ?? "BYN",
    availability: "https://schema.org/InStock",
    validFrom: festival.registrationStart,
    url: absoluteUrl(path),
  });
}

/**
 * The name the festival is presented under, not the organization's profile name.
 *
 * The two differ whenever a festival overrides its contacts, and the override is
 * what the page itself shows in the footer — search results naming the other one
 * would disagree with the page they link to. Only the detail projection carries
 * contacts; a catalog card has nothing to prefer, so it falls through.
 */
function organizerName(festival: PublicFestival | PublicFestivalDetail): string {
  const overridden = "contacts" in festival ? festival.contacts.organizationName?.trim() : null;
  return overridden || festival.organizer.name;
}

/** One competition as a schema.org `Event`. */
export function festivalEventSchema(
  festival: PublicFestival | PublicFestivalDetail,
  { path }: { path: string },
): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    ...compact({
      "@type": "Event",
      name: festival.title,
      description: festival.description,
      url: absoluteUrl(path),
      startDate: festival.competitionStart,
      // schema.org treats a missing endDate as a single-day event, which is the
      // right reading here: a festival with no end date recorded runs one day.
      endDate: festival.competitionEnd,
      eventAttendanceMode: attendanceMode(festival.modes),
      eventStatus: "https://schema.org/EventScheduled",
      image: resolveMediaUrl(festival.coverImage),
      location: place(festival),
      organizer: compact({
        "@type": "Organization",
        name: organizerName(festival),
        logo: resolveMediaUrl(festival.organizer.logo),
      }),
      offers: offers(festival, { path }),
      inLanguage: "ru-RU",
      // What the event is about, in the organizer's own vocabulary. Search uses
      // it to match "вокальный конкурс" to a festival that never says so in its
      // title.
      about: festival.categories,
    }),
  };
}

/** The catalog as an ordered list, so search can preview several festivals at once. */
export function festivalListSchema(
  festivals: readonly PublicFestival[],
  { basePath }: { basePath: string },
): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "ItemList",
    itemListElement: festivals.map((festival, index) => ({
      "@type": "ListItem",
      position: index + 1,
      // The same address the catalog links, so the list and the page it points
      // at agree on the competition's canonical URL.
      item: festivalEventSchema(festival, { path: festivalPath(festival, basePath) }),
    })),
  };
}

/** The trail from the site root to the current page. */
export function breadcrumbSchema(
  trail: readonly { name: string; path: string }[],
): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: trail.map((step, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: step.name,
      item: absoluteUrl(step.path),
    })),
  };
}
