/**
 * Public API of the `dashboard` widget — the authenticated home screen.
 *
 * A composite block (FSD widget): it assembles independent, data-driven cards
 * (stats, recent competitions/applications, notifications, events, activity)
 * into the first screen after login. It reads the session from `app/providers`
 * and its data through mocked TanStack Query hooks, composing only from
 * `shared/ui`. Pages render `<Dashboard />`; individual widgets and their pure
 * views are exported for stories/tests.
 */

export { dashboardKeys } from "./api";
export { Dashboard } from "./dashboard";
export { ActivityTimeline, ActivityTimelineView } from "./ui/activity-timeline";
export { NotificationCenter, NotificationCenterView } from "./ui/notification-center";
export { QuickActions } from "./ui/quick-actions";
export { RecentApplications, RecentApplicationsView } from "./ui/recent-applications";
export { RecentCompetitions, RecentCompetitionsView } from "./ui/recent-competitions";
export { StatCard, type StatCardProps } from "./ui/stat-card";
export { StatsGrid } from "./ui/stats-grid";
export { UpcomingEvents, UpcomingEventsView } from "./ui/upcoming-events";
export { WelcomeHeader } from "./ui/welcome-header";
