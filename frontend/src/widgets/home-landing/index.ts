/**
 * Public API of the `home-landing` widget.
 *
 * The public landing page, built from the Figma «/page-2» frame: the hero band
 * with the brand artwork, the «Ближайшие фестивали» carousel, and the closing
 * panel for organisers.
 *
 * Every piece is presentational and takes its routes and data from the page —
 * the widget never reaches for the router's auth state or builds a path of its
 * own, so the same blocks can be reused on another public surface.
 */
export { HomeFestivalCard } from "./ui/home-festival-card";
export { HomeFestivalCarousel } from "./ui/home-festival-carousel";
export { HomeHero } from "./ui/home-hero";
export { HomeOrganizersCta } from "./ui/home-organizers-cta";
export { HomeUpcomingFestivals } from "./ui/home-upcoming-festivals";
