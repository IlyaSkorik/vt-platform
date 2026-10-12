/**
 * Вход оператора платформы в кабинет организации — и выход из него.
 *
 * Оператор остаётся собой: ничего не выдаётся, ничего не отзывается, меняется
 * только то, про какую организацию следующий запрос. Поэтому вход — это запись
 * в сторе, а выход — её удаление; закрытая вкладка ничего не оставляет висеть.
 *
 * Кэш сбрасывается в обе стороны и целиком. Запросы в React Query ключуются
 * тем, что спрашивают, а не тем, у кого спрашивают: «фестивали» одной
 * организации и «фестивали» другой — это один ключ. Не сбросить — значит на
 * долю секунды показать оператору чужие строки в чужом кабинете, а это ровно то,
 * чего поддержка себе позволить не может: организатор обычно смотрит на тот же
 * экран.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useSyncExternalStore } from "react";
import { useNavigate } from "react-router";
import { type ActingOrganization, actingOrganizationStore } from "@/shared/api";
import { ROUTES } from "@/shared/config";

/** Организация, в кабинете которой оператор сейчас находится, или `null`. */
export function useActingOrganization(): ActingOrganization | null {
  return useSyncExternalStore(
    actingOrganizationStore.subscribe,
    actingOrganizationStore.get,
    () => null,
  );
}

/** Войти в кабинет организации и открыть её панель. */
export function useEnterOrganizationPanel(): (organization: ActingOrganization) => void {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useCallback(
    (organization: ActingOrganization) => {
      actingOrganizationStore.set(organization);
      queryClient.clear();
      void navigate(ROUTES.staff);
    },
    [queryClient, navigate],
  );
}

/** Выйти из кабинета и вернуться в консоль. */
export function useLeaveOrganizationPanel(): () => void {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useCallback(() => {
    actingOrganizationStore.set(null);
    queryClient.clear();
    void navigate(ROUTES.platformOrganizations);
  }, [queryClient, navigate]);
}
