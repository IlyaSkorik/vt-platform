import { useAuth } from "@/app/providers";
import { PageContainer, PageContent, PageSection } from "@/shared/ui";
import { ActivityTimeline } from "./ui/activity-timeline";
import { NotificationCenter } from "./ui/notification-center";
import { QuickActions } from "./ui/quick-actions";
import { RecentApplications } from "./ui/recent-applications";
import { RecentCompetitions } from "./ui/recent-competitions";
import { StatsGrid } from "./ui/stats-grid";
import { UpcomingEvents } from "./ui/upcoming-events";
import { WelcomeHeader } from "./ui/welcome-header";

/**
 * Dashboard — the first authenticated screen, composed from independent
 * data-driven widgets.
 *
 * Layout: a personalized welcome header, quick-action shortcuts, the headline
 * statistics row, then a responsive two-column body — recent competitions and
 * applications on the primary column, notifications and upcoming events on the
 * side — closing with the activity timeline. Each widget owns its own query and
 * its own loading/empty/error state, so a slow or failed section never blocks
 * the rest of the screen. The shell provides the chrome; this only fills the
 * content region.
 */
export function Dashboard(): React.JSX.Element {
  const { user } = useAuth();

  return (
    <PageContainer size="wide">
      <WelcomeHeader userName={user?.displayName} />

      <PageContent>
        <PageSection title="Быстрые действия" className="gap-3">
          <QuickActions />
        </PageSection>

        <PageSection aria-label="Статистика">
          <StatsGrid />
        </PageSection>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="flex flex-col gap-6 lg:col-span-2">
            <RecentCompetitions />
            <RecentApplications />
          </div>
          <div className="flex flex-col gap-6">
            <NotificationCenter />
            <UpcomingEvents />
          </div>
        </div>

        <PageSection>
          <ActivityTimeline />
        </PageSection>
      </PageContent>
    </PageContainer>
  );
}
