import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { Link } from "react-router";
import { APP_NAME, type NavModel } from "@/shared/config";
import { cn } from "@/shared/lib";
import { IconButton } from "@/shared/ui";
import { SidebarNav } from "./sidebar-nav";

interface SidebarProps {
  navigation: NavModel;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  homeHref: string;
}

/**
 * Sidebar — the persistent desktop/tablet navigation column.
 *
 * Renders as a fixed-width panel that animates to an icon rail when collapsed
 * (width transition on a motion-token duration). Contains the brand, the
 * scrollable navigation, and a collapse toggle pinned to the foot. It is an
 * ARIA `complementary` landmark so assistive tech can jump straight to it.
 */
export function Sidebar({
  navigation,
  collapsed,
  onToggleCollapsed,
  homeHref,
}: SidebarProps): React.JSX.Element {
  return (
    <aside
      aria-label="Боковая навигация"
      data-collapsed={collapsed}
      className={cn(
        "sticky top-0 hidden h-svh shrink-0 flex-col border-border border-r bg-card transition-[width] duration-normal ease-standard md:flex",
        collapsed ? "w-16" : "w-64",
      )}
    >
      <div
        className={cn(
          "flex h-16 shrink-0 items-center border-border border-b",
          collapsed ? "justify-center px-2" : "px-4",
        )}
      >
        <Link
          to={homeHref}
          className="flex items-center gap-2 rounded-md font-semibold text-foreground text-lg tracking-tight outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span
            aria-hidden="true"
            className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary font-bold text-primary-foreground text-sm"
          >
            ВТ
          </span>
          {!collapsed && <span className="truncate">{APP_NAME}</span>}
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        <SidebarNav navigation={navigation} collapsed={collapsed} />
      </div>

      <div
        className={cn(
          "flex shrink-0 border-border border-t p-2",
          collapsed ? "justify-center" : "justify-end",
        )}
      >
        <IconButton
          variant="ghost"
          size="sm"
          onClick={onToggleCollapsed}
          aria-pressed={collapsed}
          aria-label={collapsed ? "Развернуть меню" : "Свернуть меню"}
          icon={
            collapsed ? <PanelLeftOpen aria-hidden="true" /> : <PanelLeftClose aria-hidden="true" />
          }
        />
      </div>
    </aside>
  );
}
