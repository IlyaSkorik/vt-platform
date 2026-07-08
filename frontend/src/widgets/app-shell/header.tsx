import { Bell, Menu, Search } from "lucide-react";
import { IconButton } from "@/shared/ui";
import { Breadcrumbs } from "./breadcrumbs";

interface HeaderProps {
  /** Show the mobile menu button (opens the navigation drawer). */
  showMenuButton: boolean;
  onOpenMenu: () => void;
  /** App-injected right-aligned controls (theme switch, user menu…). */
  actions?: React.ReactNode;
}

/**
 * Search placeholder — a non-functional trigger that reserves the search
 * affordance and command-palette shortcut hint. Wired to real search later.
 */
function SearchPlaceholder(): React.JSX.Element {
  return (
    <button
      type="button"
      className="hidden h-9 w-full max-w-xs items-center gap-2 rounded-md border border-border bg-background px-3 text-muted-foreground text-sm outline-none transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring lg:flex"
    >
      <Search className="size-4 shrink-0" aria-hidden="true" />
      <span className="flex-1 text-left">Поиск…</span>
      <kbd className="rounded border border-border bg-muted px-1.5 font-mono text-[0.625rem] text-muted-foreground">
        ⌘K
      </kbd>
    </button>
  );
}

/**
 * Header — the sticky top bar of the Application Shell.
 *
 * Left: mobile menu button (mobile only) + breadcrumbs. Right: search and
 * notifications placeholders plus the app-injected `actions` slot (theme,
 * user menu). It is the `banner` landmark. No business logic — search and
 * notifications are visual placeholders until their features land.
 */
export function Header({ showMenuButton, onOpenMenu, actions }: HeaderProps): React.JSX.Element {
  return (
    <header className="sticky top-0 z-[var(--z-sticky)] flex h-16 shrink-0 items-center gap-3 border-border border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      {showMenuButton && (
        <IconButton
          variant="ghost"
          size="sm"
          onClick={onOpenMenu}
          aria-label="Открыть меню"
          icon={<Menu aria-hidden="true" />}
        />
      )}

      <div className="flex min-w-0 flex-1 items-center gap-4">
        <Breadcrumbs />
        <div className="ml-auto hidden flex-1 justify-end lg:flex">
          <SearchPlaceholder />
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <IconButton
          variant="ghost"
          size="sm"
          aria-label="Уведомления"
          icon={<Bell aria-hidden="true" />}
        />
        {actions}
      </div>
    </header>
  );
}
