import { Navigate, Outlet, useLocation } from "react-router";

import { useAuth } from "@/app/providers";
import { ROUTES } from "@/shared/config";

export function ProtectedRoute(): React.JSX.Element | null {
  const { status, sessionExpired } = useAuth();
  const location = useLocation();

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
