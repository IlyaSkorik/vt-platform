import { ChevronRight } from "lucide-react";
import { Fragment } from "react";
import { Link, useLocation } from "react-router";
import { resolveBreadcrumbs } from "@/shared/config";

/**
 * Breadcrumbs — derives the trail from the current pathname against the
 * navigation model (no per-route configuration needed).
 *
 * Rendered as an ordered list inside a `navigation` landmark labelled
 * "Хлебные крошки"; the current page is marked `aria-current="page"` and is
 * not a link. Renders nothing for paths outside the primary navigation, so it
 * never shows a misleading single crumb.
 */
export function Breadcrumbs(): React.JSX.Element | null {
  const location = useLocation();
  const trail = resolveBreadcrumbs(location.pathname);

  if (trail.length === 0) {
    return null;
  }

  return (
    <nav aria-label="Хлебные крошки" className="min-w-0">
      <ol className="flex items-center gap-1.5 text-sm">
        {trail.map((crumb, index) => {
          const isLast = index === trail.length - 1;
          return (
            <Fragment key={crumb.id}>
              {index > 0 && (
                <li aria-hidden="true" className="text-muted-foreground/60">
                  <ChevronRight className="size-4" />
                </li>
              )}
              <li className="min-w-0">
                {isLast || crumb.to == null ? (
                  <span
                    aria-current={isLast ? "page" : undefined}
                    className="block truncate font-medium text-foreground"
                  >
                    {crumb.label}
                  </span>
                ) : (
                  <Link
                    to={crumb.to}
                    className="block truncate rounded-sm text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {crumb.label}
                  </Link>
                )}
              </li>
            </Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
