import { ExternalLink } from "lucide-react";
import { Button } from "@/shared/ui";
import { useEnterOrganizationPanel } from "../model";

/**
 * «Войти в кабинет» на карточке организации в консоли.
 *
 * Имя организации уезжает в стор вместе с её id — не ради экономии запроса, а
 * чтобы полоса наверху панели могла назвать организацию сразу: «вы в кабинете»
 * без имени не предупреждение, а загадка.
 */
export function EnterPanelButton({
  organizationId,
  organizationName,
}: {
  organizationId: string;
  organizationName: string;
}): React.JSX.Element {
  const enter = useEnterOrganizationPanel();

  return (
    <Button variant="outline" onClick={() => enter({ id: organizationId, name: organizationName })}>
      <ExternalLink className="size-4" />
      Войти в кабинет
    </Button>
  );
}
