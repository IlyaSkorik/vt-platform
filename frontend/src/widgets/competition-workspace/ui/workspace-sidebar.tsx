import {
  COMPETITION_SECTION_GROUPS,
  type CompetitionSection,
  type CompetitionSectionId,
  competitionSectionsOfGroup,
} from "@/features/competitions";
import { cn } from "@/shared/lib";

interface WorkspaceSidebarProps {
  activeSection: CompetitionSectionId;
  onSectionChange: (sectionId: CompetitionSectionId) => void;
}

function SectionButton({
  section,
  isActive,
  onSelect,
}: {
  section: CompetitionSection;
  isActive: boolean;
  onSelect: () => void;
}): React.JSX.Element {
  const Icon = section.icon;
  return (
    <button
      type="button"
      onClick={onSelect}
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
}

/**
 * Festival configuration navigation, grouped by what the organizer is deciding.
 *
 * On desktop the groups are stacked with headings. On narrow screens the sidebar
 * collapses to one horizontal strip, where headings would cost more room than they
 * earn — there the groups are flattened and separated by a thin rule, keeping the
 * same order so the two layouts stay learnable as one thing.
 */
export function WorkspaceSidebar({
  activeSection,
  onSectionChange,
}: WorkspaceSidebarProps): React.JSX.Element {
  return (
    <aside
      aria-label="Разделы фестиваля"
      className="w-full shrink-0 border-border border-b bg-card md:w-64 md:overflow-y-auto md:border-r md:border-b-0"
    >
      <nav className="flex gap-1 overflow-x-auto p-2 md:flex-col md:gap-4 md:overflow-visible">
        {COMPETITION_SECTION_GROUPS.map((group) => (
          <div
            key={group.title}
            className="flex shrink-0 gap-1 border-border not-first:border-l not-first:pl-1 md:flex-col md:border-l-0 md:pl-0"
          >
            <p className="hidden px-3 pb-1 font-semibold text-muted-foreground text-xs uppercase tracking-wide md:block">
              {group.title}
            </p>
            {competitionSectionsOfGroup(group).map((section) => (
              <SectionButton
                key={section.id}
                section={section}
                isActive={section.id === activeSection}
                onSelect={() => onSectionChange(section.id)}
              />
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}
