import { Link } from "react-router";
import { CookieSettingsButton } from "@/features/cookie-consent";
import { APP_NAME, ROUTES } from "@/shared/config";

export function SiteFooter(): React.JSX.Element {
  const entrepreneurName = "Скорик Илья Андреевич";
  const legalStatus = "Плательщик налога на профессиональный доход";
  const unp = "УНП: AE9395951";

  return (
    <footer className="border-border/70 border-t bg-background/80 px-4 pt-8 pb-4 md:px-8">
      <div className="mx-auto grid w-full max-w-7xl gap-6 text-sm text-muted-foreground md:grid-cols-3">
        <div className="space-y-2">
          <p className="font-medium text-foreground">{APP_NAME}</p>
          <p>Платформа фестивалей и онлайн-подачи заявок.</p>
        </div>

        <div className="space-y-2">
          <p className="font-medium text-foreground">Документы</p>
          <div className="flex flex-col items-start gap-1">
            {/* First, because it is the one document that is a contract: the account
                exists because the person accepted it (LEGAL-003 §3.2). */}
            <Link to={ROUTES.termsOfService} className="hover:text-foreground hover:underline">
              Пользовательское соглашение
            </Link>
            <Link to={ROUTES.privacyPolicy} className="hover:text-foreground hover:underline">
              Политика обработки персональных данных
            </Link>
            <Link to={ROUTES.cookiesPolicy} className="hover:text-foreground hover:underline">
              Политика использования файлов cookie
            </Link>
            {/* The way back to the cookie decision. It belongs here, in the one place
                present on every page, because that is where the policy tells visitors
                to look for it (LEGAL-002 §2.4, §7.1). */}
            <CookieSettingsButton className="cursor-pointer hover:text-foreground hover:underline" />
          </div>
        </div>

        <div className="space-y-2">
          <p className="font-medium text-foreground">Реквизиты</p>
          <p>{entrepreneurName}</p>
          <p>{legalStatus}</p>
          <p>{unp}</p>
        </div>
      </div>
      <div className="mx-auto mt-6 w-full max-w-7xl border-border/70 border-t pt-4 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} {APP_NAME}
      </div>
    </footer>
  );
}
