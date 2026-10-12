import type { BeforeRequestHook } from "ky";
import { actingOrganizationStore } from "../acting-organization";
import { HEADER } from "../config";

/**
 * Acting-organization hook (request).
 *
 * Пока оператор платформы находится в кабинете организации, каждый его запрос
 * говорит, в чьём именно: сервер читает этот заголовок только у оператора и
 * только для существующей организации, так что для всех прочих он — ничего не
 * значащая строка (`apps.organization.presentation.scope`).
 *
 * Заголовок ставится здесь, а не на вызовах: кабинет — это не один экран, а
 * весь раздел `/staff`, включая сгенерированный Orval SDK, который ни о каком
 * операторе не знает и знать не должен.
 */
export const attachActingOrganization: BeforeRequestHook = ({ request }) => {
  const acting = actingOrganizationStore.get();
  if (acting !== null && !request.headers.has(HEADER.actingOrganization)) {
    request.headers.set(HEADER.actingOrganization, acting.id);
  }
};
