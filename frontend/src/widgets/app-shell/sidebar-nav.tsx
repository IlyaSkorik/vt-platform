import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { NavLink, useLocation } from "react-router";
import type { NavItem, NavModel } from "@/shared/config";
import { cn } from "@/shared/lib";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/shared/ui";

interface SidebarNavProps {
  navigation: NavModel;
  /** Rail mode: labels hidden, children collapsed, icons + tooltips only. */
  collapsed: boolean;
  /** Called after any navigation click (used to close the mobile drawer). */
  onNavigate?: (() => void) | undefined;
}

const linkBase =
  "flex items-center gap-3 rounded-md px-3 py-2 font-medium text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring";
const linkIdle = "text-muted-foreground hover:bg-accent hover:text-accent-foreground";
const linkActive = "bg-accent text-accent-foreground";

/** A leaf navigation link. Renders an accessible tooltip when collapsed. */
function NavLeaf({
  item,
  collapsed,
  nested,
  onNavigate,
}: {
  item: NavItem;
  collapsed: boolean;
  nested?: boolean | undefined;
  onNavigate?: (() => void) | undefined;
}): React.JSX.Element {
  const Icon = item.icon;
  const link = (
    <NavLink
      to={item.to ?? "#"}
      end
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          linkBase,
          isActive ? linkActive : linkIdle,
          collapsed && "justify-center px-2",
          nested && !collapsed && "pl-11",
        )
      }
    >
      {Icon != null && <Icon className="size-4 shrink-0" aria-hidden="true" />}
      {!collapsed && <span className="truncate">{item.label}</span>}
    </NavLink>
  );

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{link}</TooltipTrigger>
        <TooltipContent side="right">{item.label}</TooltipContent>
      </Tooltip>
    );
  }
  return link;
}

/** A parent item with nested children: an expand/collapse disclosure. */
function NavBranch({
  item,
  collapsed,
  onNavigate,
}: {
  item: NavItem;
  collapsed: boolean;
  onNavigate?: (() => void) | undefined;
}): React.JSX.Element {
  const location = useLocation();
  const children = item.children ?? [];
  const containsActive =
    children.some((c) => c.to === location.pathname) || item.to === location.pathname;
  const [open, setOpen] = useState<boolean>(containsActive);
  const Icon = item.icon;

  // When collapsed to a rail, a branch behaves as a leaf link to its own route
  // (children are unreachable in the rail; the header/breadcrumbs still work).
  if (collapsed) {
    return <NavLeaf item={item} collapsed onNavigate={onNavigate} />;
  }

  return (
    <li>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={cn(linkBase, "w-full", containsActive ? "text-foreground" : linkIdle)}
      >
        {Icon != null && <Icon className="size-4 shrink-0" aria-hidden="true" />}
        <span className="flex-1 truncate text-left">{item.label}</span>
        <ChevronDown
          className={cn(
            "size-4 shrink-0 transition-transform duration-normal",
            open && "rotate-180",
          )}
          aria-hidden="true"
        />
      </button>
      {open && (
        <ul className="mt-1 flex flex-col gap-1">
          {children.map((child) => (
            <li key={child.id}>
              <NavLeaf item={child} collapsed={false} nested onNavigate={onNavigate} />
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

/**
 * SidebarNav — renders the navigation model as accessible, grouped lists.
 *
 * Groups become `<ul>`s under an optional heading; items are links, and items
 * with children become keyboard-operable disclosures. Shared verbatim between
 * the desktop sidebar and the mobile drawer, so behaviour never diverges.
 */
export function SidebarNav({
  navigation,
  collapsed,
  onNavigate,
}: SidebarNavProps): React.JSX.Element {
  return (
    <nav aria-label="Основная навигация" className="flex flex-col gap-4">
      {navigation.map((group) => (
        <div key={group.id} className="flex flex-col gap-1">
          {group.label != null && !collapsed && (
            <p className="px-3 pt-1 pb-0.5 font-medium text-muted-foreground text-xs uppercase tracking-wider">
              {group.label}
            </p>
          )}
          <ul className="flex flex-col gap-1">
            {group.items.map((item) =>
              item.children != null && item.children.length > 0 ? (
                <NavBranch
                  key={item.id}
                  item={item}
                  collapsed={collapsed}
                  onNavigate={onNavigate}
                />
              ) : (
                <li key={item.id}>
                  <NavLeaf item={item} collapsed={collapsed} onNavigate={onNavigate} />
                </li>
              ),
            )}
          </ul>
        </div>
      ))}
    </nav>
  );
}
