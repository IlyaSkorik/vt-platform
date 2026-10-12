/**
 * Кто и до каких пор правит поданную заявку.
 *
 * Срок правки задаёт приём заявок, а не статус заявки: одобрение организатора и
 * даже место в расписании его не укорачивают (фамилию с заявки печатают на дипломе,
 * и опечатку исправляет тот, кто её сделал), а закрытие приёма — заканчивает. После
 * закрытия остаются ровно два случая: заявка стоит в листе ожидания — в фестиваль
 * она ещё не попала, и её состав живёт, пока живёт очередь; и организатор сам
 * вернул заявку на доработку — отказать в правке, о которой он попросил, нельзя.
 *
 * То же правило бэкенд проверяет в `ensure_submission_editable` / `ensure_order_editable`:
 * здесь оно нужно, чтобы кнопка «Редактировать» отсутствовала, а не вела в 409.
 */
import type { ApplicationResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";

/**
 * Статусы заказа, в которых его ещё правят.
 *
 * Оплата заказ не запечатывает: пока идёт приём заявок, участник правит состав и
 * номер, и оплатить пораньше не должно означать потерять право на исправление.
 * Закрыты только завершённый и отменённый.
 */
const EDITABLE_ORDER_STATUSES = new Set(["DRAFT", "SUBMITTED", "WAITING_PAYMENT", "PAID"]);

/** Whether the applicant may still edit this order right now. */
export function canApplicantEditApplication(
  application: ApplicationResource,
  registration: Registration | undefined,
): boolean {
  if (!EDITABLE_ORDER_STATUSES.has(application.status)) return false;
  if (application.hasCorrections) return true;
  if (registration?.registrationOpen === true) return true;
  // Очередь открыта не всем, а тем, кто в ней стоит: заявке, уже прошедшей приём,
  // лист ожидания закрытую дверь не отпирает.
  const queued = application.submissions.some((submission) => submission.status === "WAITLISTED");
  return queued && registration?.waitlistOpen === true;
}
