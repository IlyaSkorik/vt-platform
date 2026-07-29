import { JURY_SECTIONS, type JurySectionId } from "@/features/jury-protocols";
import { cn } from "@/shared/lib";

interface JuryWorkspaceSidebarProps {
  activeSection: JurySectionId;
  onSectionChange: (sectionId: JurySectionId) => void;
}

export function JuryWorkspaceSidebar({
  activeSection,
  onSectionChange,
}: JuryWorkspaceSidebarProps): React.JSX.Element {
  return (
    <aside
      aria-label="Разделы жюри"
      className="scrollbar-custom w-full shrink-0 border-border border-b bg-card md:w-64 md:overflow-y-auto md:border-r md:border-b-0"
    >
      <nav className="scrollbar-custom flex gap-1 overflow-x-auto p-2 md:flex-col md:overflow-visible">
        {JURY_SECTIONS.map((section) => {
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
              {/* Said out loud rather than hidden: an organizer looking for the jury's
                  roster should learn it is coming, not conclude it is missing. */}
              {!section.implemented && (
                <span className="ml-auto shrink-0 text-[10px] text-muted-foreground uppercase tracking-wide">
                  позже
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
