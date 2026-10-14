/**
 * Исправление заявки организатором — за участника, прямо в карточке.
 *
 * Заявка хранит снимок данных участника, а не ссылку на них, поэтому опечатку
 * можно починить в самой заявке, не трогая реестр. Ручка нужна ровно тогда, когда
 * ошибку заметили поздно: одобрение уводит номер сразу в программу фестиваля, и
 * «вернуть на исправление» из этого статуса уже нельзя.
 *
 * Отправляется целиком тот раздел, который открыт: сервер сам считает разницу и
 * сам решает, о чём написать участнику. Раздел, который не передали, он не трогает —
 * поэтому форма, где правили только номер, не обнулит педагогов.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient, humanMessage } from "@/shared/api";

/** Строка справочника фестиваля: то, из чего можно выбрать. */
export type TaxonomyOption = { id: string; name: string };

/** Номинация живёт внутри жанра, поэтому несёт его с собой. */
export type TaxonomyDisciplineOption = TaxonomyOption & { nominationId: string };

/** Возрастная категория заведена под конкретный состав — иначе форма предложит чужую. */
export type TaxonomyAgeOption = TaxonomyOption & { participantGroupId: string };

export type SubmissionTaxonomy = {
  nominations: TaxonomyOption[];
  disciplines: TaxonomyDisciplineOption[];
  participantGroups: TaxonomyOption[];
  ageCategories: TaxonomyAgeOption[];
  participationFormats: TaxonomyOption[];
};

/**
 * Выступающий так, как он лежит в заявке: солист — частями имени, коллектив — названием.
 *
 * Учреждение приходит двумя полями, и путать их нельзя.
 * `organizationName` — исправленное организатором в самой заявке; у подавляющего
 * большинства выступающих его нет (`null`), и это значит «никто не правил», а не
 * «учреждения нет». `resolvedOrganizationName` — то, что печатается сейчас:
 * исправленное, если оно есть, иначе из реестра участника в кабинете заявителя.
 * Форма открывается на втором, а отправляет первое — см. `correctionOrganization`.
 */
export type CorrectablePerformer = {
  id: string;
  displayName?: string | null;
  firstName?: string | null;
  lastName?: string | null;
  middleName?: string | null;
  birthDate?: string | null;
  gender?: string | null;
  memberCount: number;
  members?: string[];
  organizationName?: string | null;
  resolvedOrganizationName?: string | null;
};

export type CorrectableTeacher = {
  id: string;
  firstName?: string | null;
  lastName?: string | null;
  middleName?: string | null;
  role: string;
};

/** Один номер заявки со всем, что в нём можно исправить. */
export type CorrectablePerformance = {
  submissionId: string;
  title: string;
  status: string;
  /** Разрешает ли статус правку — считает сервер, кнопка только слушается. */
  canEditContent?: boolean;
  durationSeconds?: number | null;
  comment?: string | null;
  ageComposition?: string | null;
  nominationId?: string | null;
  disciplineId?: string | null;
  ageCategoryId?: string | null;
  participantGroupId?: string | null;
  participationFormatId?: string | null;
  participants?: CorrectablePerformer[];
  teachers?: CorrectableTeacher[];
};

export type CorrectionPayload = {
  performance: {
    title: string;
    durationSeconds: number;
    nominationId: string;
    disciplineId: string;
    ageCategoryId: string;
    participantGroupId: string;
    participationFormatId: string;
    comment: string;
    ageComposition: string;
  };
  participants: Array<{
    id?: string;
    displayName?: string | null;
    firstName?: string | null;
    lastName?: string | null;
    middleName?: string | null;
    birthDate?: string | null;
    gender?: string | null;
    memberCount: number;
    members: string[];
    organizationName: string | null;
  }>;
  teachers: Array<{
    id?: string;
    firstName: string;
    lastName: string;
    middleName?: string | null;
    role: string;
  }>;
  comment: string;
};

/**
 * Что отправить в `organizationName` для одного выступающего.
 *
 * Пустое поле — это «брать из реестра», а не «учреждения нет»: организатор, который
 * его стёр, отменяет правку, а не утверждает, что участник ниоткуда.
 *
 * И главное: значение, совпавшее с тем, что и так печаталось, не закрепляется. Форма
 * открыта на реестровом учреждении, и если его не трогали — отправляется `null`.
 * Иначе каждое сохранение любой другой правки молча отвязывало бы заявку от реестра,
 * и заявка, поданная год назад, перестала бы следовать за переименованием школы.
 */
export function correctionOrganization(
  typed: string,
  performer: Pick<CorrectablePerformer, "organizationName" | "resolvedOrganizationName">,
): string | null {
  const value = typed.trim();
  if (!value) {
    return null;
  }
  const pinned = (performer.organizationName ?? "").trim();
  const resolved = (performer.resolvedOrganizationName ?? "").trim();
  if (!pinned && value === resolved) {
    return null;
  }
  return value;
}

/** Что сервер посчитал изменённым — теми же словами, что уйдут участнику в письме. */
export type CorrectionResult = { id: string; status: string; changes: string[] };

async function correct(
  submissionId: string,
  payload: CorrectionPayload,
): Promise<CorrectionResult> {
  try {
    const response = await apiClient.put(`staff/applications/${submissionId}/content`, {
      json: payload,
    });
    const body = (await response.json()) as { data: CorrectionResult };
    return body.data;
  } catch (error) {
    const response = (error as { response?: Response })?.response;
    if (response) {
      const body = (await response.json().catch(() => null)) as {
        detail?: string;
        title?: string;
        message?: string;
        error?: string;
      } | null;
      throw new Error(
        humanMessage(body?.detail ?? body?.message ?? body?.error ?? body?.title, response.status),
      );
    }
    throw error;
  }
}

/**
 * Сохранить исправление и перечитать очередь.
 *
 * Очередь инвалидируется всегда: правка меняет и карточку, и строку в списке
 * (участник в подписи, длительность в подсчёте по жанру), а карточка открыта рядом
 * со списком, из которого её выбрали.
 */
export function useCorrectSubmission() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ submissionId, payload }: { submissionId: string; payload: CorrectionPayload }) =>
      correct(submissionId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["staff", "applications", "workspace"] });
    },
  });
}
