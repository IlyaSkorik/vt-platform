import { LogOut, ShieldUser } from "lucide-react";
import type { ActingOrganization } from "@/shared/api";
import { Button } from "@/shared/ui";
import { useActingOrganization, useLeaveOrganizationPanel } from "../model";

/**
 * Полоса поверх панели: чей это кабинет и как из него выйти.
 *
 * Единственное, что отличает этот экран от собственного кабинета оператора, —
 * заголовок в запросах, которого не видно. Без полосы оператор через десять
 * минут правит чужой фестиваль, будучи уверен, что правит свой: ошибка тихая,
 * необратимая и совершается на глазах у самого организатора.
 *
 * Поэтому она не прячется при прокрутке и несёт кнопку выхода: уйти должно быть
 * ровно так же просто, как войти, и не через консоль.
 */
export function ActingAsBanner(): React.JSX.Element | null {
  const acting = useActingOrganization();

  // Выход вытащен в отдельный компонент не ради композиции: он берёт из
  // контекста очередь запросов и роутер, а эта полоса висит в каркасе панели,
  // которым пользуются все. Спрашивать провайдеры ради строки, которой у
  // организатора не бывает никогда, — значит требовать их со всех.
  return acting === null ? null : <Banner organization={acting} />;
}

function Banner({ organization }: { organization: ActingOrganization }): React.JSX.Element {
  const leave = useLeaveOrganizationPanel();

  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 border-warning/30 border-b bg-warning-surface px-4 py-2 text-sm text-warning"
    >
      <ShieldUser className="size-4 shrink-0" aria-hidden="true" />
      <p className="min-w-0 flex-1">
        Вы в кабинете <span className="font-medium">«{organization.name}»</span> как оператор
        платформы. Всё, что вы здесь измените, будет сделано от имени организации.
      </p>
      <Button size="sm" variant="outline" onClick={leave}>
        <LogOut className="size-4" />
        Выйти из кабинета
      </Button>
    </div>
  );
}
