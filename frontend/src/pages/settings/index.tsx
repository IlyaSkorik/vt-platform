import { useAuth, useTheme } from "@/app/providers";
import {
  AppearanceCard,
  ConsentsCard,
  EmailCard,
  PasswordCard,
  PhoneCard,
  type ThemePreference,
} from "@/features/account-settings";
import {
  LoadingState,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
} from "@/shared/ui";

/**
 * `/cabinet/settings` — "Настройки".
 *
 * The account itself, as opposed to the заявки made with it: how to sign in, how
 * to be reached, what has been consented to, and how the interface looks. One card per thing that can change,
 * each its own form, so a failed password change never costs somebody the phone
 * number they typed above it.
 *
 * The account comes from the shell's `GET /users/me`, which is also what the
 * header renders, so a change is re-read once here and appears everywhere.
 */
export function SettingsPage(): React.JSX.Element {
  const { user, refresh } = useAuth();
  const { theme, setTheme } = useTheme();

  if (!user) {
    return (
      <PageContainer size="narrow">
        <PageContent>
          <LoadingState label="Загружаем настройки…" />
        </PageContent>
      </PageContainer>
    );
  }

  return (
    <PageContainer size="narrow">
      <PageHeader>
        <PageTitle>Настройки</PageTitle>
        <PageDescription>
          Аккаунт {user.displayName}. Здесь меняются доступ к кабинету, контакты, согласия и
          оформление.
        </PageDescription>
      </PageHeader>
      <PageContent>
        <div className="flex flex-col gap-6">
          <EmailCard email={user.email} verified={user.emailVerified} onChanged={() => refresh()} />
          <PasswordCard />
          <PhoneCard phone={user.phone ?? null} onChanged={() => refresh()} />
          {/* The withdrawal channel the policy promises in the cabinet (LEGAL-001 §13.4).
              Placed among the account cards rather than on a page of its own: a right
              nobody can find is not a right that has been given. */}
          <ConsentsCard />
          <AppearanceCard
            theme={theme as ThemePreference}
            onThemeChange={(next) => setTheme(next)}
          />
        </div>
      </PageContent>
    </PageContainer>
  );
}
