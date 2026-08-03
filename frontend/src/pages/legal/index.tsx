import { ROUTES } from "@/shared/config";
import { useSeo } from "@/shared/seo";
import { PageContainer, PageContent, PageDescription, PageHeader, PageTitle } from "@/shared/ui";

function LegalPage({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}): React.JSX.Element {
  // Indexable on purpose: a findable privacy policy is part of being a service
  // parents are asked to trust with a child's data, and search engines treat its
  // presence as a quality signal for the domain.
  useSeo({ title, description });

  return (
    <PageContainer size="wide" className="px-4 md:px-8">
      <PageHeader>
        <PageTitle>{title}</PageTitle>
        <PageDescription>{description}</PageDescription>
      </PageHeader>
      <PageContent className="max-w-4xl space-y-6 text-sm leading-6">{children}</PageContent>
    </PageContainer>
  );
}

export function PrivacyPolicyPage(): React.JSX.Element {
  return (
    <LegalPage
      title="Политика обработки персональных данных"
      description="Документ определяет, какие персональные данные мы обрабатываем и для каких целей."
    >
      <section className="space-y-2">
        <h2 className="text-base font-semibold">1. Общие положения</h2>
        <p>
          Настоящая политика применяется ко всем данным, которые пользователь предоставляет при
          регистрации, подаче заявок и использовании сервиса.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold">2. Какие данные обрабатываются</h2>
        <p>
          ФИО, контакты, сведения из профиля участника и педагога, данные заявок и служебная
          техническая информация о сессии.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold">3. Цели обработки</h2>
        <p>
          Идентификация пользователя, работа личного кабинета, приём и сопровождение заявок,
          исполнение обязательств перед пользователем и соблюдение требований законодательства.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold">4. Контакты</h2>
        <p>
          По вопросам обработки персональных данных используйте форму обратной связи в сервисе или
          официальные контакты, указанные внизу сайта.
        </p>
      </section>

      <p className="text-xs text-muted-foreground">
        Ссылка на раздел: <a href={ROUTES.privacyPolicy}>{ROUTES.privacyPolicy}</a>
      </p>
    </LegalPage>
  );
}

export function CookiesPolicyPage(): React.JSX.Element {
  return (
    <LegalPage
      title="Политика использования cookies"
      description="Документ описывает, какие cookie-файлы используются и как ими управлять."
    >
      <section className="space-y-2">
        <h2 className="text-base font-semibold">1. Что такое cookies</h2>
        <p>
          Cookies — это небольшие файлы, которые сохраняются в браузере и помогают корректной работе
          сервиса.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold">2. Какие cookies используются</h2>
        <p>
          Технические cookies для авторизации, безопасности сессии и корректной работы интерфейса.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-base font-semibold">3. Управление cookies</h2>
        <p>
          Пользователь может ограничить или удалить cookies в настройках браузера, но это может
          повлиять на работу личного кабинета и авторизацию.
        </p>
      </section>

      <p className="text-xs text-muted-foreground">
        Ссылка на раздел: <a href={ROUTES.cookiesPolicy}>{ROUTES.cookiesPolicy}</a>
      </p>
    </LegalPage>
  );
}
