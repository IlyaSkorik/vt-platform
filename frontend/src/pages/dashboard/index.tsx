import { Dashboard } from "@/widgets/dashboard";

/**
 * Dashboard page — the first screen after successful authentication.
 *
 * A thin route entry: the screen itself is the `dashboard` widget, which owns
 * all composition and data fetching. Rendered inside the Application Shell via
 * the protected route tree.
 */
export function DashboardPage(): React.JSX.Element {
  return <Dashboard />;
}
