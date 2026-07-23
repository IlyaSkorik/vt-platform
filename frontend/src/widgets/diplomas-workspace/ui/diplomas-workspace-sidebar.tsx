import { DIPLOMA_SECTIONS, type DiplomaSectionId } from "@/features/diplomas";
import { cn } from "@/shared/lib";

interface DiplomasWorkspaceSidebarProps {
  activeSection: DiplomaSectionId;
  onSectionChange: (sectionId: DiplomaSectionId) => void;
}

export function DiplomasWorkspaceSidebar({
  activeSection,
  onSectionChange,
}: DiplomasWorkspaceSidebarProps): React.JSX.Element {
  return (
    <aside
      aria-label="Разделы дипломов"
      className="w-full shrink-0 border-border border-b bg-card md:w-64 md:overflow-y-auto md:border-r md:border-b-0"
    >
      <nav className="flex gap-1 overflow-x-auto p-2 md:flex-col md:overflow-visible">
        {DIPLOMA_SECTIONS.map((section) => {
          const Icon = section.icon;
          const isActive = section.id === activeSection;
          return (
            <button
              key={section.id}
              type="button"
              onClick={() => onSectionChange(section.id)}
              className={cn(
                "flex min-h-9 shrink-0 items-center gap-2 rounded-md px-3 py-2 text-left text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring",
                isActive
                  ? "bg-accent font-medium text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/70 hover:text-accent-foreground",
              )}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon className="size-4 shrink-0" aria-hidden="true" />
              <span className="truncate">{section.title}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
