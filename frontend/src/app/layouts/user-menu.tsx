import { LogOut, User as UserIcon } from "lucide-react";
import { DropdownMenu } from "radix-ui";
import { useNavigate } from "react-router";
import { useAuth } from "@/app/providers";
import { ROUTES } from "@/shared/config";
import { Avatar } from "@/shared/ui";

/**
 * User menu (app layer).
 *
 * Lives in `app/layouts` (not the shell widget) because it depends on the auth
 * session, an app-level concern. Rendered into the shell via the `headerActions`
 * slot. Provides account navigation and sign-out, wired to the AuthProvider —
 * signing out revokes the session (`DELETE /auth/sessions/current`) and routes
 * back to login. Token-styled and keyboard-navigable (Radix DropdownMenu).
 */
export function UserMenu(): React.JSX.Element {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const name = user?.displayName ?? "Гость";
  const initials =
    name
      .split(" ")
      .map((part) => part.charAt(0))
      .slice(0, 2)
      .join("")
      .toUpperCase() || "Г";

  const handleSignOut = async (): Promise<void> => {
    await signOut();
    navigate(ROUTES.login, { replace: true });
  };

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger
        aria-label="Меню пользователя"
        className="flex items-center gap-2 rounded-full outline-none transition-opacity hover:opacity-90 focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Avatar size="sm" fallback={initials} />
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={8}
          className="z-dropdown min-w-52 rounded-md border bg-popover p-1 text-popover-foreground shadow-elevation-2"
        >
          {user ? (
            <div className="px-2 py-1.5">
              <p className="truncate font-medium text-sm">{user.displayName}</p>
              <p className="truncate text-muted-foreground text-xs">{user.email}</p>
            </div>
          ) : null}
          <DropdownMenu.Separator className="my-1 h-px bg-border" />
          <DropdownMenu.Item
            onSelect={() => navigate(ROUTES.profile)}
            className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground [&_svg]:size-4"
          >
            <UserIcon aria-hidden="true" />
            Профиль
          </DropdownMenu.Item>
          <DropdownMenu.Item
            onSelect={(event) => {
              event.preventDefault();
              void handleSignOut();
            }}
            className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-danger text-sm outline-none data-[highlighted]:bg-danger-surface [&_svg]:size-4"
          >
            <LogOut aria-hidden="true" />
            Выйти
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
