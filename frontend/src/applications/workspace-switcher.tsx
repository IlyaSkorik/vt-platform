import { BriefcaseBusiness, ShieldCheck, User } from "lucide-react";
import { NavLink } from "react-router";

import { useAuth } from "@/app/providers";
import { ROUTES } from "@/shared/config";
import { cn } from "@/shared/lib";

type WorkspaceSwitcherProps = {
  className?: string;
};

const linkClassName = ({ isActive }: { isActive: boolean }) =>
  cn(
    "inline-flex min-h-9 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring",
    isActive
      ? "bg-primary text-primary-foreground shadow-elevation-1"
      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
  );

export function WorkspaceSwitcher({ className }: WorkspaceSwitcherProps): React.JSX.Element {
  // Each destination is offered only to whoever the matching route guard would
  // actually admit, so the switcher never links somewhere that bounces back:
  // `/staff` needs a membership (`StaffRoute`), `/platform` needs the grant
  // (`PlatformRoute`), and the two are independent — a platform operator need
  // not belong to any organization, and an organization's owner is not an operator.
  const { staffMembership, isPlatformAdmin } = useAuth();

  return (
    <nav
      aria-label="Переключение рабочего пространства"
      className={cn("flex items-center rounded-lg border border-border bg-muted/40 p-1", className)}
    >
      <NavLink to={ROUTES.cabinet} className={linkClassName}>
        <User className="size-4" aria-hidden="true" />
        <span>Личный кабинет</span>
      </NavLink>
      {staffMembership ? (
        <NavLink to={ROUTES.staff} className={linkClassName}>
          <BriefcaseBusiness className="size-4" aria-hidden="true" />
          <span>Панель управления</span>
        </NavLink>
      ) : null}
      {isPlatformAdmin ? (
        <NavLink to={ROUTES.platform} className={linkClassName}>
          <ShieldCheck className="size-4" aria-hidden="true" />
          <span>Платформа</span>
        </NavLink>
      ) : null}
    </nav>
  );
}
