import { Navigate, Outlet, useLocation } from "react-router";

import { type AuthModule, useAuth } from "@/app/providers";
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

/**
 * A staff route that also needs the organization to hold a given module.
 *
 * Stacked on top of `StaffRoute` rather than replacing it: being staff says the
 * person may be in the panel at all, and this says their organization was sold
 * the part of it they are pointing at.
 *
 * Convenience only. The module gate that *matters* is on the API — every staff
 * endpoint of a module is behind `IsModuleEnabled`, so a hand-typed URL renders
 * a page whose every request comes back 403. This guard exists so the person
 * lands somewhere sensible instead of on a screen of failures.
 *
 * The platform operator is exempt for the same reason the server exempts them:
 * they are staff of no organization, so "which modules does theirs hold" is not
 * a question with an answer.
 */
export function ModuleRoute({ module }: { module: AuthModule }): React.JSX.Element | null {
  const { status, isPlatformAdmin, hasModule } = useAuth();
  usePrivateSectionSeo();

  if (status === "loading") {
    return null;
  }

  if (!isPlatformAdmin && !hasModule(module)) {
    return <Navigate to={ROUTES.staff} replace />;
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
