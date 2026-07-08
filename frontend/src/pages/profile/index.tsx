import {
  Card,
  CardContent,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
} from "@/shared/ui";

/**
 * Profile page (placeholder).
 *
 * Renders inside the Application Shell using the page primitives. Self-service
 * profile editing (`GET`/`PATCH /users/me`, API-001 §4.8) is delivered later.
 */
export function ProfilePage(): React.JSX.Element {
  return (
    <PageContainer size="narrow">
      <PageHeader>
        <PageTitle>Профиль</PageTitle>
        <PageDescription>Управление аккаунтом и настройками.</PageDescription>
      </PageHeader>
      <PageContent>
        <Card>
          <CardContent className="pt-6 text-muted-foreground text-sm">
            Настройки профиля появятся здесь.
          </CardContent>
        </Card>
      </PageContent>
    </PageContainer>
  );
}
