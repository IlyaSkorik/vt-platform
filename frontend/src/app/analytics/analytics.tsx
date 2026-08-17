import { useEffect, useRef } from "react";
import { useLocation } from "react-router";
import { useAnalyticsConsent } from "@/features/cookie-consent";
import { startAnalytics, stopAnalytics, trackPageView } from "./trackers";

/**
 * The counters, tied to the visitor's decision and to the address bar.
 *
 * Renders nothing. It sits inside the router (so it can see navigations) and reads
 * the consent store (so it can see the decision), and it is the only thing that
 * calls into `trackers.ts`:
 *
 * - no decision, or "only necessary" → nothing is loaded, nothing is sent;
 * - "accept all" → the counters load and the current page is recorded;
 * - a decision withdrawn later → the counters are stopped, their cookies expired,
 *   and the page reloads, because a tag already in the document cannot be taken
 *   back any other way (LEGAL-002 §2.6).
 */
export function Analytics(): null {
  const allowed = useAnalyticsConsent();
  const { pathname, search } = useLocation();
  const running = useRef(false);

  useEffect(() => {
    if (allowed) {
      running.current = startAnalytics();
      return;
    }
    // Nothing to withdraw if this page never started counting: a first visit with
    // the banner still open must not reload itself out from under the visitor.
    if (!running.current) {
      return;
    }
    running.current = false;
    if (stopAnalytics()) {
      window.location.reload();
    }
  }, [allowed]);

  useEffect(() => {
    if (!allowed) {
      return;
    }
    trackPageView(`${pathname}${search}`);
  }, [allowed, pathname, search]);

  return null;
}
