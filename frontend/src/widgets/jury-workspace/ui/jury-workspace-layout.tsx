import type { ReactNode } from "react";
import type { JurySectionId } from "@/features/jury-protocols";
import { JuryWorkspaceHeader } from "./jury-workspace-header";
import { JuryWorkspaceSidebar } from "./jury-workspace-sidebar";

interface JuryWorkspaceLayoutProps {
  activeSection: JurySectionId;
  sectionTitle: string;
  sectionDescription: string;
  onSectionChange: (sectionId: JurySectionId) => void;
  children: ReactNode;
}

export function JuryWorkspaceLayout({
  activeSection,
  sectionTitle,
  sectionDescription,
  onSectionChange,
  children,
}: JuryWorkspaceLayoutProps): React.JSX.Element {
  return (
    <div className="-mx-4 -mt-4 flex min-h-[calc(100svh-8rem)] flex-col overflow-hidden rounded-lg border bg-background md:-mx-6 md:-mt-6 lg:-mx-8">
      <JuryWorkspaceHeader sectionTitle={sectionTitle} sectionDescription={sectionDescription} />
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <JuryWorkspaceSidebar activeSection={activeSection} onSectionChange={onSectionChange} />
        <section
          // `overflow-x-hidden` is not decoration: `overflow-y-auto` on its own coerces
          // `overflow-x` from `visible` to `auto`, which made this section scroll sideways
          // whenever its content was wider than it — dragging the protocol's heading, its
          // banner and its toolbar along with the table. Sideways scrolling belongs to the
          // table's own wrapper, which has it, and to nothing above that.
          className="scrollbar-custom min-w-0 flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-6"
          aria-label="Содержимое раздела жюри"
        >
          {children}
        </section>
      </div>
    </div>
  );
}
