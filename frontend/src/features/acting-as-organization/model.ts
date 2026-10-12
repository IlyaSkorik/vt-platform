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
 *
 * Вход ждёт ответа сервера и проверяет его. Панель рисуется из `/users/me`, и
 * если сервер заголовок не прочёл — не та версия бэкенда, отозванный доступ
 * оператора, организация, которой больше нет, — то ответ приходит прежний, «вы
 * не сотрудник», и `/staff` молча возвращает нажавшего в кабинет. Молча — это и
 * есть худшее: кнопка нажата, ничего не произошло, причины не названо.
 */
import { hashKey, useQueryClient } from "@tanstack/react-query";
import { useCallback, useSyncExternalStore } from "react";
import { useNavigate } from "react-router";
import { authKeys } from "@/features/auth";
import { type ActingOrganization, actingOrganizationStore } from "@/shared/api";
import type { CurrentUser } from "@/shared/api/generated/model";
import { ROUTES } from "@/shared/config";
import { toast } from "@/shared/ui";

/** Организация, в кабинете которой оператор сейчас находится, или `null`. */
export function useActingOrganization(): ActingOrganization | null {
  return useSyncExternalStore(
    actingOrganizationStore.subscribe,
    actingOrganizationStore.get,
    () => null,
  );
}

/** Войти в кабинет организации и открыть её панель. */
export function useEnterOrganizationPanel(): (organization: ActingOrganization) => Promise<void> {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useCallback(
    async (organization: ActingOrganization) => {
      actingOrganizationStore.set(organization);
      // Ответы, снятые до входа, относятся к другой организации — их не должно
      // остаться ни в одном кэше. Сессию трогаем отдельно: её надо не выбросить,
      // а переспросить, потому что именно по ней решается, пускать ли в панель.
      const sessionHash = hashKey(authKeys.currentUser);
      queryClient.removeQueries({ predicate: (query) => query.queryHash !== sessionHash });
      await queryClient.refetchQueries({ queryKey: authKeys.currentUser });

      const session = queryClient.getQueryData<CurrentUser>(authKeys.currentUser);
      if (session?.staffMembership?.organizationId !== organization.id) {
        actingOrganizationStore.set(null);
        await queryClient.refetchQueries({ queryKey: authKeys.currentUser });
        toast.error(
          `Не удалось войти в кабинет «${organization.name}»: сервер не признал заход. Проверьте, что доступ оператора в силе, а API обновлён.`,
        );
        return;
      }

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
