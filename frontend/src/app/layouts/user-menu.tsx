import { useAuth } from "@/app/providers";
import { Avatar } from "@/shared/ui";

/**
 * User menu — PLACEHOLDER (app layer).
 *
 * Lives in `app/layouts` (not the shell widget) because it depends on the auth
 * session, which is an app-level concern. Rendered into the shell through the
 * `headerActions` slot. For bootstrap it shows an avatar affordance only; the
 * Auth feature replaces the body with a real menu (profile, sign out) against
 * the Identity API (API-001).
 */
export function UserMenu(): React.JSX.Element {
  const { user } = useAuth();
  const name = user?.displayName ?? "Гость";
  const initials = name
    .split(" ")
    .map((part) => part.charAt(0))
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <button
      type="button"
      aria-label="Меню пользователя"
      className="flex items-center gap-2 rounded-full outline-none transition-opacity hover:opacity-90 focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Avatar size="sm" fallback={initials || "Г"} />
    </button>
  );
}
