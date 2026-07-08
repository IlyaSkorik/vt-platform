import type { LucideIcon } from "lucide-react";
import { Award, FileText, PlusCircle, ScrollText, UserPlus } from "lucide-react";
import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Card } from "@/shared/ui";

interface QuickAction {
  readonly id: string;
  readonly label: string;
  readonly description: string;
  readonly to: string;
  readonly icon: LucideIcon;
}

/** The primary tasks an organizer starts from the dashboard (mission scope). */
const ACTIONS: readonly QuickAction[] = [
  {
    id: "register-participant",
    label: "Регистрация участника",
    description: "Добавить нового участника в реестр",
    to: ROUTES.participants,
    icon: UserPlus,
  },
  {
    id: "create-competition",
    label: "Создать конкурс",
    description: "Настроить новый конкурс и номинации",
    to: ROUTES.competitions,
    icon: PlusCircle,
  },
  {
    id: "view-applications",
    label: "Заявки",
    description: "Просмотреть и обработать заявки",
    to: ROUTES.applications,
    icon: FileText,
  },
  {
    id: "results",
    label: "Результаты",
    description: "Подвести и опубликовать итоги",
    to: ROUTES.results,
    icon: Award,
  },
  {
    id: "certificates",
    label: "Сертификаты",
    description: "Сформировать дипломы и сертификаты",
    to: ROUTES.results,
    icon: ScrollText,
  },
];

/**
 * QuickActions — a grid of shortcut cards to the platform's primary tasks.
 *
 * Each card is a full-area router link (the whole surface is the hit target,
 * WCAG 2.5.5) with an icon, label and one-line description. Purely
 * navigational and stateless; token-only styling with a visible focus ring.
 */
export function QuickActions(): React.JSX.Element {
  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {ACTIONS.map((action) => {
        const Icon = action.icon;
        return (
          <li key={action.id}>
            <Card className="h-full transition-colors hover:border-primary/40 hover:bg-accent/40">
              <Link
                to={action.to}
                className="flex h-full flex-col gap-2 rounded-lg p-4 outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span
                  aria-hidden="true"
                  className="flex size-9 items-center justify-center rounded-md bg-primary/10 text-primary [&_svg]:size-5"
                >
                  <Icon />
                </span>
                <span className="font-medium text-foreground text-sm">{action.label}</span>
                <span className="text-muted-foreground text-xs">{action.description}</span>
              </Link>
            </Card>
          </li>
        );
      })}
    </ul>
  );
}
