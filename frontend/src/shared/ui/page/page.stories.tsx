import type { Meta, StoryObj } from "@storybook/react-vite";
import { Plus } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";
import {
  EmptyPage,
  PageActions,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageSection,
  PageTitle,
} from ".";

/**
 * The page layout primitives compose the skeleton of every screen rendered
 * inside the Application Shell: a width-constrained container, a header with
 * title/description/actions, and titled content sections.
 */
const meta = {
  title: "Shell/Page Layout",
  parameters: { layout: "fullscreen" },
  tags: ["autodocs"],
} satisfies Meta;

export default meta;

type Story = StoryObj<typeof meta>;

export const FullPage: Story = {
  render: () => (
    <div className="min-h-svh bg-background p-8">
      <PageContainer>
        <PageHeader actions={<Button leftIcon={<Plus aria-hidden="true" />}>Добавить</Button>}>
          <PageTitle>Участники</PageTitle>
          <PageDescription>Список участников и управление ими.</PageDescription>
        </PageHeader>
        <PageContent>
          <PageSection title="Активные" description="Участники с открытыми заявками.">
            <Card>
              <CardHeader>
                <CardTitle>Таблица</CardTitle>
              </CardHeader>
              <CardContent className="text-muted-foreground text-sm">
                Содержимое раздела.
              </CardContent>
            </Card>
          </PageSection>
          <PageSection title="Архив" actions={<Button variant="outline">Экспорт</Button>}>
            <Card>
              <CardContent className="pt-6 text-muted-foreground text-sm">
                Архивные записи.
              </CardContent>
            </Card>
          </PageSection>
        </PageContent>
      </PageContainer>
    </div>
  ),
};

export const HeaderWithActions: Story = {
  render: () => (
    <div className="bg-background p-8">
      <PageContainer>
        <PageHeader
          actions={
            <PageActions>
              <Button variant="outline">Отмена</Button>
              <Button>Сохранить</Button>
            </PageActions>
          }
        >
          <PageTitle>Настройки конкурса</PageTitle>
          <PageDescription>Основные параметры и расписание.</PageDescription>
        </PageHeader>
      </PageContainer>
    </div>
  ),
};

export const Empty: Story = {
  render: () => (
    <div className="bg-background p-8">
      <PageContainer>
        <PageHeader>
          <PageTitle>Финансы</PageTitle>
          <PageDescription>Платежи, счета и отчётность.</PageDescription>
        </PageHeader>
        <PageContent>
          <EmptyPage
            title="Раздел в разработке"
            description="Финансовый модуль появится в одном из ближайших релизов."
            action={<Button variant="outline">Вернуться в кабинет</Button>}
          />
        </PageContent>
      </PageContainer>
    </div>
  ),
};
