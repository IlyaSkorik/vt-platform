import { Link } from "react-router";
import { APP_NAME, ROUTES } from "@/shared/config";

export function SiteFooter(): React.JSX.Element {
  const entrepreneurName = "Скорик Илья Андреевич";
  const legalStatus = "Самозанятый";
  const unp = "УНП: ..";

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
            <Link to={ROUTES.privacyPolicy} className="hover:text-foreground hover:underline">
              Политика обработки персональных данных
            </Link>
            <Link to={ROUTES.cookiesPolicy} className="hover:text-foreground hover:underline">
              Политика обработки файлов cookies
            </Link>
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
