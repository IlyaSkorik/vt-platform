/**
 * The two counters, and everything that keeps them on the right side of consent.
 *
 * Yandex Metrica and Google Analytics are loaded from here and nowhere else — not
 * from `index.html`, because a tag in the document head runs before the visitor has
 * been asked anything, and `mc.yandex.ru` has then already been told who they are.
 * LEGAL-002 §2.4 says in as many words that nothing analytic loads before consent,
 * so the script tags are created only when {@link startAnalytics} is called, and it
 * is called only by the consent-aware component in `analytics.tsx`.
 *
 * Both counters are put in manual page-view mode. This is a single-page app: the
 * document loads once and the address changes thereafter without it, so a counter
 * left on automatic would record one visit and then nothing at all.
 *
 * The ids come from the build (`VITE_YANDEX_METRICA_ID`, `VITE_GA_MEASUREMENT_ID`).
 * An empty id is not an error — it is a build with no counter, which is what every
 * environment but production wants.
 */
import { env } from "@/shared/config";

const METRICA_TAG_URL = "https://mc.yandex.ru/metrika/tag.js";
const GTAG_URL = "https://www.googletagmanager.com/gtag/js";

/** The queue the Metrica tag drains once it arrives: calls in `.a`, load time in `.l`. */
type Ym = ((...args: unknown[]) => void) & { a?: unknown[][]; l?: number };

declare global {
  interface Window {
    ym?: Ym;
    dataLayer?: unknown[];
  }
}

/** Whether a counter was loaded into this page. */
let loaded = false;

function metricaId(): number | null {
  const raw = env.yandexMetricaId;
  return raw === "" ? null : Number(raw);
}

function gaId(): string | null {
  return env.googleAnalyticsId === "" ? null : env.googleAnalyticsId;
}

/** Whether this build carries any counter at all. */
export function analyticsConfigured(): boolean {
  return metricaId() !== null || gaId() !== null;
}

function appendScript(src: string): void {
  const script = document.createElement("script");
  script.async = true;
  script.src = src;
  document.head.appendChild(script);
}

function startMetrica(counter: number): void {
  if (window.ym === undefined) {
    // The counter's own stub, kept faithful to the published snippet: calls made
    // before the tag arrives are queued on `.a` and replayed by it.
    const queue: Ym = (...args: unknown[]) => {
      queue.a = queue.a ?? [];
      queue.a.push(args);
    };
    queue.l = Date.now();
    window.ym = queue;
    // The id rides on the tag URL, as the counter's own snippet has it.
    appendScript(`${METRICA_TAG_URL}?id=${counter}`);
  }
  window.ym(counter, "init", {
    // `defer` suppresses the automatic first hit — every hit, including the first,
    // is sent by `trackPageView`, so the two counters agree on what a view is and
    // a route change is not silently missed.
    defer: true,
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    // Declared to visitors as `_ym_visorc` in LEGAL-002 §4.1. Turning it off here
    // is one word; the policy would then be promising more than we collect, which
    // is the harmless direction.
    webvisor: true,
    // As configured on the counter itself. Nothing pushes commerce events yet;
    // Metrica only reads entries carrying an `ecommerce` key, and gtag pushes none.
    ecommerce: "dataLayer",
  });
}

/**
 * One gtag command, pushed the way gtag.js insists on receiving it.
 *
 * The published snippet is `function gtag(){dataLayer.push(arguments)}`, and the
 * `arguments` there is not incidental. The tag walks `dataLayer` and treats an
 * entry as a command only when it is an Arguments object; a plain array is taken
 * for a data push and its command is never run. Pushing `[...args]` therefore
 * loads gtag.js, queues everything, and sends nothing — so the real `arguments`
 * object is what goes on the queue, rest parameters serving only to type it.
 */
function gtag(..._args: unknown[]): void {
  window.dataLayer = window.dataLayer ?? [];
  // biome-ignore lint/complexity/noArguments: gtag.js runs Arguments objects and ignores arrays
  window.dataLayer.push(arguments);
}

function startGoogleAnalytics(measurementId: string): void {
  window.dataLayer = window.dataLayer ?? [];
  appendScript(`${GTAG_URL}?id=${encodeURIComponent(measurementId)}`);
  gtag("js", new Date());
  gtag("config", measurementId, { send_page_view: false });
}

/**
 * Load whichever counters this build carries. Safe to call more than once.
 *
 * Returns whether anything is now running, so the caller can tell "the visitor
 * agreed" from "the visitor agreed and there was nothing to load".
 */
export function startAnalytics(): boolean {
  if (loaded) {
    return true;
  }
  const counter = metricaId();
  const measurement = gaId();
  if (counter === null && measurement === null) {
    return false;
  }
  if (counter !== null) {
    startMetrica(counter);
  }
  if (measurement !== null) {
    startGoogleAnalytics(measurement);
  }
  loaded = true;
  return true;
}

/**
 * Record one page view. Does nothing until the counters are running.
 *
 * `path` is what the router navigated to; the absolute URL is derived from it so
 * both counters are told the same address.
 */
export function trackPageView(path: string, title: string = document.title): void {
  if (!loaded) {
    return;
  }
  const url = new URL(path, window.location.origin).toString();
  const counter = metricaId();
  if (counter !== null && window.ym !== undefined) {
    window.ym(counter, "hit", url, { title });
  }
  const measurement = gaId();
  if (measurement !== null) {
    gtag("event", "page_view", { page_location: url, page_path: path, page_title: title });
  }
}

/** Cookie names the two services set on our own domain (LEGAL-002 §4.1). */
function isAnalyticsCookie(name: string): boolean {
  return name.startsWith("_ym_") || name === "ymex" || name === "_ga" || name.startsWith("_ga_");
}

function forgetCookie(name: string): void {
  const expiry = "Thu, 01 Jan 1970 00:00:00 GMT";
  const host = window.location.hostname;
  // The same cookie can be written against the host or the registrable domain, and
  // a delete only lands on an exact match — so both are asked to expire.
  const domains = [undefined, host, `.${host.split(".").slice(-2).join(".")}`];
  for (const domain of domains) {
    const scope = domain === undefined ? "" : `; domain=${domain}`;
    // biome-ignore lint/suspicious/noDocumentCookie: the Cookie Store API is not in Safari or Firefox, and expiring a third party's cookie is exactly what this must do
    document.cookie = `${name}=; expires=${expiry}; path=/${scope}`;
  }
}

/**
 * Stop counting, as far as a page that already loaded a tag can.
 *
 * LEGAL-002 §2.6 promises that withdrawing consent ends the use of analytics
 * cookies. A tag cannot be unloaded, so this does the three things that can be
 * done from here: tells Google to disable itself, expires the cookies both
 * services set on our domain, and reports back that something *was* running — the
 * caller reloads on that, and after the reload nothing loads at all, because
 * consent is gone.
 */
export function stopAnalytics(): boolean {
  const measurement = gaId();
  if (measurement !== null) {
    // The opt-out switch gtag.js checks on every call, by measurement id.
    (window as unknown as Record<string, boolean>)[`ga-disable-${measurement}`] = true;
  }
  for (const pair of document.cookie.split(";")) {
    const name = pair.split("=")[0]?.trim();
    if (name !== undefined && name !== "" && isAnalyticsCookie(name)) {
      forgetCookie(name);
    }
  }
  const wasRunning = loaded;
  loaded = false;
  return wasRunning;
}

/** Testing seam: forget that anything was loaded. */
export function resetAnalyticsForTests(): void {
  loaded = false;
  delete window.ym;
  delete window.dataLayer;
}
