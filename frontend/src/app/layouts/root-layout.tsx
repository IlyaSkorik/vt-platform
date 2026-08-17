import { Suspense } from "react";
import { Outlet, ScrollRestoration } from "react-router";
import { Analytics } from "@/app/analytics";
import { CookieBanner } from "@/features/cookie-consent";

/**
 * Root layout — the outermost route element.
 *
 * Provides scroll restoration between navigations and a Suspense boundary for
 * lazily-loaded route modules. It renders no chrome itself; nested layouts
 * (auth, cabinet) own their visual shells. A skip link keeps keyboard
 * navigation accessible (WCAG 2.1 AA).
 *
 * The cookie bar is mounted here rather than in the public layout because the
 * decision it collects is about the visitor, not about a section of the site: it
 * has to be asked once, wherever they land — including a diploma-verification
 * link or a programme page that never passes through the marketing shell.
 */
export function RootLayout(): React.JSX.Element {
  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Перейти к содержимому
      </a>
      <div id="main-content" className="min-h-svh">
        <Suspense fallback={<RouteFallback />}>
          <Outlet />
        </Suspense>
      </div>
      <ScrollRestoration />
      <CookieBanner />
      {/* Beside the banner on purpose: the counters answer to the decision it
          collects, and both belong wherever the visitor happens to land. */}
      <Analytics />
    </>
  );
}

function RouteFallback(): React.JSX.Element {
  return (
    <div className="flex min-h-svh items-center justify-center" aria-live="polite" aria-busy="true">
      <div
        className="size-6 animate-spin rounded-full border-2 border-muted border-t-primary"
        role="status"
      >
        <span className="sr-only">Загрузка…</span>
      </div>
    </div>
  );
}
