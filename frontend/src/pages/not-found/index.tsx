import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { useSeo } from "@/shared/seo";
import { Button } from "@/shared/ui";

/**
 * 404 page — rendered inside `NotFoundLayout` for any unmatched route.
 */
export function NotFoundPage(): React.JSX.Element {
  // A single-page app answers 200 to everything, so the only thing telling a
  // crawler this URL is a dead end is the tag. Without it every typo'd address
  // becomes an indexable duplicate of the 404 screen.
  useSeo({ title: "Страница не найдена", robots: "noindex" });

  return (
    <div className="flex flex-col items-center justify-center gap-4 text-center">
      <p className="font-mono text-muted-foreground text-6xl">404</p>
      <div className="space-y-2">
        <h1 className="font-bold text-3xl tracking-tight">Страница не найдена</h1>
        <p className="max-w-md text-muted-foreground text-sm">
          Возможно, ссылка устарела или страница была перемещена.
        </p>
      </div>
      <Button asChild>
        <Link to={ROUTES.home}>На главную</Link>
      </Button>
    </div>
  );
}
