import { BriefcaseBusiness, Home } from "lucide-react";
import { NavLink } from "react-router";

import { ROUTES } from "@/shared/config";
import { cn } from "@/shared/lib";

type WorkspaceSwitcherProps = {
  className?: string;
};

const linkClassName = ({ isActive }: { isActive: boolean }) =>
  cn(
    "inline-flex min-h-9 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-slate-900 text-white shadow-sm"
      : "text-slate-600 hover:bg-slate-100 hover:text-slate-950",
  );

export function WorkspaceSwitcher({ className }: WorkspaceSwitcherProps): React.JSX.Element {
  return (
    <nav
      aria-label="Переключение рабочего пространства"
      className={cn("flex items-center gap-1", className)}
    >
      <NavLink to={ROUTES.cabinet} className={linkClassName}>
        <Home className="h-4 w-4" aria-hidden="true" />
        <span>Личный кабинет</span>
      </NavLink>
      <NavLink to={ROUTES.staff} className={linkClassName}>
        <BriefcaseBusiness className="h-4 w-4" aria-hidden="true" />
        <span>Панель управления</span>
      </NavLink>
    </nav>
  );
}
