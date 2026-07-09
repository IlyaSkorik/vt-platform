import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "@/app/providers";
import { ROUTES } from "@/shared/config";

/**
 * ProtectedRoute — gates authenticated areas.
 *
 * Unauthenticated visitors are redirected: to `/session-expired` when a live
 * session just dropped (so the user understands why), otherwise to `/login`
 * with the attempted location preserved in router state for return-after-login.
 * While the session is resolving, nothing is rendered. No authentication logic
 * lives here — it only reads status from context.
 */
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

/**
 * GuestRoute — gates guest-only areas (login, register, password reset).
 *
 * Authenticated users are bounced to the personal cabinet (the platform's home
 * for every account) so they never see the auth screens while signed in. Staff
 * access remains an opt-in area and never becomes a landing page.
 */
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
