import { Navigate, Outlet, useLocation } from "react-router";

import { useAuth } from "@/app/providers";
import { APP_NAME, ROUTES } from "@/shared/config";
import { useSectionSeo } from "@/shared/seo";

/**
 * Everything behind a sign-in is closed to crawlers, declared at the gate.
 *
 * The alternative — a `noindex` on each of the ~58 cabinet, staff and operator
 * routes — is a rule enforced by memory, and the first page added without it
 * leaks. Here the guard that makes a route private is the same place that makes
 * it unindexable, so the two can't drift apart. The refusal is sticky: a page
 * inside may still name itself without re-opening the section.
 */
function usePrivateSectionSeo(): void {
  useSectionSeo({ title: APP_NAME, standaloneTitle: true, robots: "noindex" });
}

export function ProtectedRoute(): React.JSX.Element | null {
  const { status, sessionExpired } = useAuth();
  const location = useLocation();
  usePrivateSectionSeo();

  if (status === "loading") {
    return null;
  }

  if (status === "unauthenticated") {
    if (sessionExpired) {
      return <Navigate to={ROUTES.sessionExpired} replace />;
    }

    return <Navigate to={ROUTES.login} replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function StaffRoute(): React.JSX.Element | null {
  const { status, sessionExpired, staffMembership } = useAuth();
  const location = useLocation();
  usePrivateSectionSeo();

  if (status === "loading") {
    return null;
  }

  if (status === "unauthenticated") {
    if (sessionExpired) {
      return <Navigate to={ROUTES.sessionExpired} replace />;
    }

    return <Navigate to={ROUTES.login} replace state={{ from: location }} />;
  }

  if (staffMembership == null) {
    return <Navigate to={ROUTES.cabinet} replace />;
  }

  return <Outlet />;
}

export function PlatformRoute(): React.JSX.Element | null {
  const { status, sessionExpired, isPlatformAdmin } = useAuth();
  const location = useLocation();
  usePrivateSectionSeo();

  if (status === "loading") {
    return null;
  }

  if (status === "unauthenticated") {
    if (sessionExpired) {
      return <Navigate to={ROUTES.sessionExpired} replace />;
    }

    return <Navigate to={ROUTES.login} replace state={{ from: location }} />;
  }

  // Not the staff gate: being an organization's owner grants nothing here.
  if (!isPlatformAdmin) {
    return <Navigate to={ROUTES.cabinet} replace />;
  }

  return <Outlet />;
}

export function GuestRoute(): React.JSX.Element | null {
  const { status } = useAuth();

  if (status === "loading") {
    return null;
  }

  if (status === "authenticated") {
    return <Navigate to={ROUTES.cabinet} replace />;
  }

  return <Outlet />;
}
