import { useMemo } from "react";
import { useSearchParams } from "react-router";
import {
  DEFAULT_DIPLOMA_SECTION,
  type DiplomaSectionId,
  findDiplomaSection,
} from "@/features/diplomas";
import { PageContainer } from "@/shared/ui";
import {
  ArchiveSection,
  AssignmentsSection,
  DiplomasWorkspaceLayout,
  GenerationSection,
  TemplatesSection,
} from "@/widgets/diplomas-workspace";

export function StaffDiplomasPage(): React.JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();

  const activeSection = (searchParams.get("section") ??
    DEFAULT_DIPLOMA_SECTION) as DiplomaSectionId;
  const section = useMemo(() => findDiplomaSection(activeSection), [activeSection]);

  const handleSectionChange = (nextSection: DiplomaSectionId): void => {
    setSearchParams({ section: nextSection }, { replace: true });
  };

  return (
    <PageContainer size="full" className="gap-0">
      <DiplomasWorkspaceLayout
        activeSection={section.id}
        sectionTitle={section.title}
        sectionDescription={section.description}
        onSectionChange={handleSectionChange}
      >
        {section.id === "templates" ? (
          <TemplatesSection />
        ) : section.id === "assignments" ? (
          <AssignmentsSection />
        ) : section.id === "generation" ? (
          <GenerationSection />
        ) : (
          <ArchiveSection />
        )}
      </DiplomasWorkspaceLayout>
    </PageContainer>
  );
}
