import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import {
  type AutosaveState,
  buildPublicationChecklist,
  type CompetitionSectionId,
  DEFAULT_COMPETITION_SECTION,
  findCompetitionSection,
  useArchiveCompetitionMutation,
  useCloseRegistrationMutation,
  useCompetitionDetail,
  useMarkConfiguredMutation,
  useMarkReadyMutation,
  useOpenRegistrationMutation,
  usePublishCompetitionMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import { ROUTES } from "@/shared/config";
import { Alert, Button, EmptyState, PageContainer, Skeleton, toast } from "@/shared/ui";
import { AdditionalServicesSection } from "@/widgets/competition-additional-services";
import { AdmissionRulesSection } from "@/widgets/competition-admission-rules";
import { AgeCategoriesSection } from "@/widgets/competition-age-categories";
import { CategoriesSection } from "@/widgets/competition-categories";
import { ContactsSection } from "@/widgets/competition-contacts";
import { DocumentsSection } from "@/widgets/competition-documents";
import { GeneralSection } from "@/widgets/competition-general";
import { ParticipantGroupsSection } from "@/widgets/competition-participant-groups";
import { ParticipationFormatsSection } from "@/widgets/competition-participation-formats";
import { PricingSection } from "@/widgets/competition-pricing";
import { PublicInformationSection } from "@/widgets/competition-public-information";
import { RegulationsSection } from "@/widgets/competition-regulations";
import { SettingsSection } from "@/widgets/competition-settings";
import { CompetitionWorkspaceLayout, SectionPlaceholder } from "@/widgets/competition-workspace";

function WorkspaceSkeleton(): React.JSX.Element {
  return (
    <div role="status" aria-label="Загрузка рабочего пространства фестиваля" className="space-y-4">
      <Skeleton className="h-20 w-full" />
      <div className="grid gap-4 lg:grid-cols-[16rem_1fr]">
        <Skeleton className="h-96 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    </div>
  );
}

export function StaffCompetitionWorkspacePage(): React.JSX.Element {
  const { competitionId } = useParams<{ competitionId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [autosaveState, setAutosaveState] = useState<AutosaveState>("idle");

  const activeSection = (searchParams.get("section") ??
    DEFAULT_COMPETITION_SECTION) as CompetitionSectionId;
  const section = useMemo(() => findCompetitionSection(activeSection), [activeSection]);

  const detailQuery = useCompetitionDetail(competitionId);
  const publish = usePublishCompetitionMutation();
  const markConfigured = useMarkConfiguredMutation();
  const markReady = useMarkReadyMutation();
  const openRegistration = useOpenRegistrationMutation();
  const closeRegistration = useCloseRegistrationMutation();
  const archive = useArchiveCompetitionMutation();

  const checklist = useMemo(
    () => (detailQuery.data ? buildPublicationChecklist(detailQuery.data) : null),
    [detailQuery.data],
  );

  const handleSectionChange = (nextSection: CompetitionSectionId): void => {
    setSearchParams({ section: nextSection }, { replace: true });
  };

  const runLifecycleAction = async (
    action: () => Promise<unknown>,
    successMessage: string,
    failureMessage: string,
  ): Promise<void> => {
    try {
      await action();
      toast.success(successMessage);
    } catch (error) {
      const message =
        error instanceof ApiError ? (error.problem?.detail ?? failureMessage) : failureMessage;
      toast.error(message);
    }
  };

  if (detailQuery.isLoading) {
    return (
      <PageContainer size="full">
        <WorkspaceSkeleton />
      </PageContainer>
    );
  }

  if (detailQuery.isError) {
    return (
      <PageContainer size="narrow">
        <EmptyState
          title="Не удалось открыть фестиваль"
          description="Фестиваль мог быть удалён, либо у вас нет доступа."
          action={
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void detailQuery.refetch()}>Повторить</Button>
              <Button asChild variant="outline">
                <Link to={ROUTES.staffCompetitions}>К списку фестивалей</Link>
              </Button>
            </div>
          }
        />
      </PageContainer>
    );
  }

  const competition = detailQuery.data;
  if (!competition || !checklist) {
    return (
      <PageContainer size="narrow">
        <Alert variant="danger" title="Фестиваль не найден" />
      </PageContainer>
    );
  }

  return (
    <PageContainer size="full" className="gap-0">
      <CompetitionWorkspaceLayout
        competition={competition}
        activeSection={section.id}
        autosaveState={autosaveState}
        checklist={checklist}
        onSectionChange={handleSectionChange}
        onPublish={() =>
          void runLifecycleAction(
            () => publish.mutateAsync(competition.id),
            "Фестиваль опубликован",
            "Не удалось опубликовать фестиваль",
          )
        }
        onMarkConfigured={() =>
          void runLifecycleAction(
            () => markConfigured.mutateAsync(competition.id),
            "Фестиваль отмечен как настроенный",
            "Не удалось отметить фестиваль как настроенный",
          )
        }
        onMarkReady={() =>
          void runLifecycleAction(
            () => markReady.mutateAsync(competition.id),
            "Фестиваль отмечен как готовый",
            "Не удалось отметить фестиваль как готовый",
          )
        }
        onOpenRegistration={() =>
          void runLifecycleAction(
            () => openRegistration.mutateAsync(competition.id),
            "Регистрация открыта",
            "Не удалось открыть регистрацию",
          )
        }
        onCloseRegistration={() =>
          void runLifecycleAction(
            () => closeRegistration.mutateAsync(competition.id),
            "Регистрация закрыта",
            "Не удалось закрыть регистрацию",
          )
        }
        onArchive={() =>
          void runLifecycleAction(
            () => archive.mutateAsync(competition.id),
            "Фестиваль архивирован",
            "Не удалось архивировать фестиваль",
          )
        }
        publishing={publish.isPending}
        markingConfigured={markConfigured.isPending}
        markingReady={markReady.isPending}
        openingRegistration={openRegistration.isPending}
        closingRegistration={closeRegistration.isPending}
        archiving={archive.isPending}
      >
        {section.id === "general" ? (
          <GeneralSection
            competition={competition}
            checklist={checklist}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "regulations" ? (
          <RegulationsSection
            competition={competition}
            checklist={checklist}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "documents" ? (
          <DocumentsSection
            competition={competition}
            checklist={checklist}
            isLoading={detailQuery.isFetching && !detailQuery.isFetched}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "categories" ? (
          <CategoriesSection
            competition={competition}
            checklist={checklist}
            isLoading={detailQuery.isFetching && !detailQuery.isFetched}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "age-categories" ? (
          <AgeCategoriesSection
            competition={competition}
            checklist={checklist}
            isLoading={detailQuery.isFetching && !detailQuery.isFetched}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "participant-groups" ? (
          <ParticipantGroupsSection
            competition={competition}
            checklist={checklist}
            isLoading={detailQuery.isFetching && !detailQuery.isFetched}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "participation-formats" ? (
          <ParticipationFormatsSection
            competition={competition}
            checklist={checklist}
            isLoading={detailQuery.isFetching && !detailQuery.isFetched}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "admission-rules" ? (
          <AdmissionRulesSection
            competition={competition}
            checklist={checklist}
            isLoading={detailQuery.isFetching && !detailQuery.isFetched}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "pricing" ? (
          <PricingSection
            competition={competition}
            checklist={checklist}
            isLoading={detailQuery.isFetching && !detailQuery.isFetched}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "additional-services" ? (
          <AdditionalServicesSection
            competition={competition}
            checklist={checklist}
            isLoading={detailQuery.isFetching && !detailQuery.isFetched}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "settings" ? (
          <SettingsSection
            competition={competition}
            checklist={checklist}
            isLoading={detailQuery.isFetching && !detailQuery.isFetched}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "contacts" ? (
          <ContactsSection
            competition={competition}
            checklist={checklist}
            isLoading={detailQuery.isFetching && !detailQuery.isFetched}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : section.id === "public-information" ? (
          <PublicInformationSection
            competition={competition}
            checklist={checklist}
            isLoading={detailQuery.isFetching && !detailQuery.isFetched}
            onAutosaveStateChange={setAutosaveState}
            onNavigateSection={handleSectionChange}
          />
        ) : (
          <SectionPlaceholder
            title={section.title}
            checklist={checklist}
            onNavigateSection={handleSectionChange}
          />
        )}
      </CompetitionWorkspaceLayout>
    </PageContainer>
  );
}
