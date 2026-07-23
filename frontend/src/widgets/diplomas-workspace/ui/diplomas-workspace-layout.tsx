import type { ReactNode } from "react";
import type { DiplomaSectionId } from "@/features/diplomas";
import { DiplomasWorkspaceHeader } from "./diplomas-workspace-header";
import { DiplomasWorkspaceSidebar } from "./diplomas-workspace-sidebar";

interface DiplomasWorkspaceLayoutProps {
  activeSection: DiplomaSectionId;
  sectionTitle: string;
  sectionDescription: string;
  onSectionChange: (sectionId: DiplomaSectionId) => void;
  children: ReactNode;
}

export function DiplomasWorkspaceLayout({
  activeSection,
  sectionTitle,
  sectionDescription,
  onSectionChange,
  children,
}: DiplomasWorkspaceLayoutProps): React.JSX.Element {
  return (
    <div className="-mx-4 -mt-4 flex min-h-[calc(100svh-8rem)] flex-col overflow-hidden rounded-lg border bg-background md:-mx-6 md:-mt-6 lg:-mx-8">
      <DiplomasWorkspaceHeader
        sectionTitle={sectionTitle}
        sectionDescription={sectionDescription}
      />
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <DiplomasWorkspaceSidebar activeSection={activeSection} onSectionChange={onSectionChange} />
        <section
          className="min-w-0 flex-1 overflow-y-auto p-4 md:p-6"
          aria-label="Содержимое раздела дипломов"
        >
          {children}
        </section>
      </div>
    </div>
  );
}
