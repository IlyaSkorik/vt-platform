import type { Meta, StoryObj } from "@storybook/react-vite";
import { Bell, Moon } from "lucide-react";
import { MemoryRouter } from "react-router";
import { ROUTES } from "@/shared/config";
import {
  Avatar,
  Card,
  CardContent,
  IconButton,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
} from "@/shared/ui";
import { AppShell } from "./app-shell";

/**
 * The Application Shell — the permanent authenticated layout. Every story is
 * wrapped in a router (the shell uses links/breadcrumbs) and mounted at a
 * route so navigation active-state and breadcrumbs resolve.
 *
 * Use the viewport toolbar (or the dedicated Mobile story) to review the
 * responsive drawer behaviour, and the theme toolbar for VT Light / VT Dark.
 */
const meta = {
  title: "Shell/AppShell",
  component: AppShell,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story, context) => (
      <MemoryRouter initialEntries={[(context.parameters.route as string) ?? ROUTES.cabinet]}>
        <Story />
      </MemoryRouter>
    ),
  ],
} satisfies Meta<typeof AppShell>;

export default meta;

type Story = StoryObj<typeof meta>;

/** Header controls the app injects into the shell's `headerActions` slot. */
const headerActions = (
  <>
    <IconButton variant="ghost" size="sm" aria-label="Тема" icon={<Moon aria-hidden="true" />} />
    <button type="button" aria-label="Меню пользователя" className="rounded-full">
      <Avatar size="sm" fallback="ИС" />
    </button>
  </>
);

function DemoPage({ title }: { title: string }): React.JSX.Element {
  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>{title}</PageTitle>
        <PageDescription>Пример страницы, отрендеренной внутри оболочки.</PageDescription>
      </PageHeader>
      <PageContent>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {["Конкурсы", "Заявки", "Судейство"].map((c) => (
            <Card key={c}>
              <CardContent className="pt-6">
                <h2 className="font-medium text-sm">{c}</h2>
                <p className="mt-2 text-muted-foreground text-sm">Данные появятся здесь.</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </PageContent>
    </PageContainer>
  );
}

export const Desktop: Story = {
  args: { headerActions, children: <DemoPage title="Кабинет" /> },
};

export const CollapsedSidebar: Story = {
  args: { headerActions, children: <DemoPage title="Кабинет" /> },
  parameters: {
    docs: {
      description: {
        story: "Use the collapse toggle at the foot of the sidebar to switch to the icon rail.",
      },
    },
  },
};

export const NestedRouteBreadcrumbs: Story = {
  args: { headerActions, children: <DemoPage title="Заявки" /> },
  parameters: { route: "/applications" },
};

export const Mobile: Story = {
  args: { headerActions, children: <DemoPage title="Кабинет" /> },
  globals: { viewport: { value: "mobile1", isRotated: false } },
  parameters: {
    docs: {
      description: {
        story:
          "Below the `md` breakpoint the sidebar collapses into a drawer opened from the header menu button.",
      },
    },
  },
};

export const Tablet: Story = {
  args: { headerActions, children: <DemoPage title="Кабинет" /> },
  globals: { viewport: { value: "tablet", isRotated: false } },
};

export const WithNotificationsAction: Story = {
  args: {
    children: <DemoPage title="Кабинет" />,
    headerActions: (
      <>
        <IconButton
          variant="ghost"
          size="sm"
          aria-label="Уведомления"
          icon={<Bell aria-hidden="true" />}
        />
        {headerActions}
      </>
    ),
  },
};
