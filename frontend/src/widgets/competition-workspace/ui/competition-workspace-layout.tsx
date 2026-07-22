import type { ReactNode } from "react";
import type {
  AutosaveState,
  CompetitionSectionId,
  PublicationChecklist,
} from "@/features/competitions";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import { WorkspaceHeader } from "./workspace-header";
import { WorkspaceSidebar } from "./workspace-sidebar";

interface CompetitionWorkspaceLayoutProps {
  competition: CompetitionDetail;
  activeSection: CompetitionSectionId;
  autosaveState: AutosaveState;
  checklist: PublicationChecklist;
  onSectionChange: (sectionId: CompetitionSectionId) => void;
  onPublish: () => void;
  onMarkConfigured: () => void;
  onMarkReady: () => void;
  onStart: () => void;
  onComplete: () => void;
  publishing?: boolean;
  markingConfigured?: boolean;
  markingReady?: boolean;
  starting?: boolean;
  completing?: boolean;
  children: ReactNode;
}

export function CompetitionWorkspaceLayout({
  competition,
  activeSection,
  autosaveState,
  checklist,
  onSectionChange,
  onPublish,
  onMarkConfigured,
  onMarkReady,
  onStart,
  onComplete,
  publishing,
  markingConfigured,
  markingReady,
  starting,
  completing,
  children,
}: CompetitionWorkspaceLayoutProps): React.JSX.Element {
  return (
    <div className="-mx-4 -mt-4 flex min-h-[calc(100svh-8rem)] flex-col overflow-hidden rounded-lg border bg-background md:-mx-6 md:-mt-6 lg:-mx-8">
      <WorkspaceHeader
        competition={competition}
        autosaveState={autosaveState}
        checklist={checklist}
        onPublish={onPublish}
        onMarkConfigured={onMarkConfigured}
        onMarkReady={onMarkReady}
        onStart={onStart}
        onComplete={onComplete}
        {...(publishing !== undefined ? { publishing } : {})}
        {...(markingConfigured !== undefined ? { markingConfigured } : {})}
        {...(markingReady !== undefined ? { markingReady } : {})}
        {...(starting !== undefined ? { starting } : {})}
        {...(completing !== undefined ? { completing } : {})}
      />
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <WorkspaceSidebar activeSection={activeSection} onSectionChange={onSectionChange} />
        <section
          className="min-w-0 flex-1 overflow-y-auto p-4 md:p-6"
          aria-label="Содержимое раздела фестиваля"
        >
          {children}
        </section>
      </div>
    </div>
  );
}
