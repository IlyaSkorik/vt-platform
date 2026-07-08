import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "@/app/providers";
import { ROUTES } from "@/shared/config";

/**
 * ProtectedRoute — gates authenticated areas.
 *
 * Unauthenticated visitors are redirected to login, preserving the attempted
 * location in router state so the Auth feature can return them afterwards.
 * While the session is resolving, nothing is rendered (a splash/skeleton will
 * be added with the Auth feature). No authentication logic lives here — it only
 * reads the auth status from context.
 */
export function ProtectedRoute(): React.JSX.Element | null {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return null;
  }

  if (status === "unauthenticated") {
    return <Navigate to={ROUTES.login} replace state={{ from: location }} />;
  }

  return <Outlet />;
}

/**
 * GuestRoute — gates guest-only areas (login, register, password reset).
 *
 * Authenticated users are bounced to the dashboard so they never see the auth
 * screens while signed in.
 */
export function GuestRoute(): React.JSX.Element | null {
  const { status } = useAuth();

  if (status === "loading") {
    return null;
  }

  if (status === "authenticated") {
    return <Navigate to={ROUTES.dashboard} replace />;
  }

  return <Outlet />;
}
