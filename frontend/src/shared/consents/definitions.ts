/**
 * The consent texts, in one place, with the version of each.
 *
 * Every checkbox that asks for a consent renders its wording from here, and the same
 * entry supplies the `(consentType, version)` pair recorded in the journal — so what
 * the server stores always identifies what the person actually read (LEGAL-001 §13.3).
 * Two copies of a consent text drifting apart is the failure this module exists to
 * prevent.
 *
 * **Versions are append-only.** A wording that changes gets a new `version`; editing a
 * version in place would silently rewrite what past acceptances mean. Codes match the
 * backend: `apps.identity` `ConsentType` for account consents, and the registration
 * projection's requirement codes for application consents.
 *
 * The texts themselves paraphrase nothing — each states the purpose, the data and the
 * consequence of refusing, and points at the clause of the published policy it rests
 * on (`docs/legal/LEGAL-001-privacy-policy.md`).
 */

/** A consent as the platform asks for it and records it. */
export type ConsentDefinition = {
  /** Wire code: what the journal stores as `consentType`. */
  readonly code: string;
  /** Version of *this text*. New wording, new version — never an in-place edit. */
  readonly version: string;
  /** Whether the flow may proceed without it. */
  readonly required: boolean;
  /** The one-line statement beside the checkbox. */
  readonly summary: string;
  /** The full wording, disclosed on request beneath the checkbox. */
  readonly text: string;
  /**
   * Codes this one acceptance records, when it stands for more than its own.
   *
   * Only the terms checkbox uses it: what that box states is that the terms are
   * accepted *and* the policies have been read, which are two entries in the journal
   * and one decision by the person.
   */
  readonly records?: readonly string[];
};

/** Current version of every consent text below. Bump per text, not globally. */
const V1 = "1.0";

/**
 * Consents collected at registration.
 *
 * Terms acceptance and acknowledging the policies travel in one checkbox: accepting the
 * terms is entering an agreement, and confirming you have read the policies is not a
 * separate permission to process anything. The permission itself — `data_processing` —
 * is asked for separately, because a consent bundled with anything else is not freely
 * given.
 */
export const ACCOUNT_CONSENTS: readonly ConsentDefinition[] = [
  {
    code: "terms_of_service",
    version: V1,
    required: true,
    records: ["terms_of_service", "privacy_policy"],
    summary:
      "Я принимаю условия использования Платформы и подтверждаю, что ознакомлен(а) с Политикой обработки персональных данных и Политикой использования файлов cookie.",
    text: "Принимая условия использования Платформы, я подтверждаю, что ознакомлен(а) с Политикой в отношении обработки персональных данных и Политикой использования файлов cookie, включая сведения об Операторе, целях и правовых основаниях обработки, сроках хранения персональных данных и порядке реализации моих прав, установленном разделом 15 Политики.",
  },
  {
    code: "data_processing",
    version: V1,
    required: true,
    summary:
      "Я даю согласие на обработку моих персональных данных для создания учётной записи, приёма заявок и направления уведомлений.",
    text: "Я даю согласие Оператору — Скорику Илье Андреевичу (УНП AE9395951) — на обработку моих персональных данных: фамилии, имени, отчества, адреса электронной почты, номера телефона (при указании), сведений об учреждении и должности, а также сведений об учётной записи и сеансах работы. Цели обработки: регистрация и обслуживание учётной записи, аутентификация, приём и сопровождение заявок на участие, направление уведомлений, связанных с оказанием услуг, исполнение обязанностей, возложенных на Оператора законодательством. Обработка осуществляется способами и в сроки, указанные в разделах 7 и 11 Политики. Согласие может быть отозвано в любое время без объяснения причин в порядке, установленном разделом 13 Политики; отзыв влечёт прекращение обработки и удаление персональных данных, за исключением данных, хранение которых предусмотрено законодательством.",
  },
  {
    code: "marketing",
    version: V1,
    required: false,
    summary:
      "Я согласен(на) получать информационные рассылки о фестивалях и конкурсах. Отказ не влияет на участие.",
    text: "Я даю согласие на обработку моего адреса электронной почты, фамилии и имени для направления информационных рассылок о фестивалях, конкурсах и иных мероприятиях, проводимых на Платформе. Отказ от предоставления этого согласия либо его отзыв не влечёт ограничения участия в мероприятиях и доступа к функциям Платформы. Согласие может быть отозвано в любое время — в личном кабинете либо по ссылке отказа, содержащейся в каждом информационном сообщении.",
  },
];

/**
 * The consent that authorises holding a child's data at all.
 *
 * Asked of whoever enters the child — a legal representative for their own child, or a
 * teacher who must already hold the representative's consent (LEGAL-001 §5.4, §6.3).
 * One wording covers both, because in both cases the statement being made is the same:
 * the representative has consented.
 */
export const PARTICIPANT_CONSENT: ConsentDefinition = {
  code: "minor_data_processing",
  version: V1,
  required: true,
  summary:
    "Согласие законного представителя участника на обработку его персональных данных получено, и я подтверждаю его предоставление.",
  text: "Я подтверждаю, что являюсь законным представителем участника либо располагаю согласием его законного представителя на обработку персональных данных участника, и даю (подтверждаю) согласие на обработку персональных данных участника: фамилии, имени, отчества, даты рождения (для определения возрастной категории), изображения (фотографии) участника, сведений об учреждении, коллективе и педагоге, сведений о заявках, творческих работах и результатах их оценивания — в объёме, указанном в разделе 5 Политики в отношении обработки персональных данных, в целях участия в фестивалях и конкурсах, проводимых на Платформе. Творческая работа передаётся жюри с указанием псевдонима участника. Согласие может быть отозвано в любое время; отзыв влечёт прекращение обработки персональных данных участника, их удаление и невозможность дальнейшего участия в мероприятии (разделы 6 и 13 Политики).",
};

/**
 * The consent that authorises holding a teacher's details.
 *
 * A teacher in somebody's directory is an adult whose data is being entered by another
 * person, and the platform never speaks to them at that moment. So the statement made
 * here is the one §5.4 of the policy requires of whoever enters another person's data:
 * their consent has already been obtained. The wording is a confirmation, not a consent
 * given on the teacher's behalf — nobody can consent for an adult who is not present.
 */
export const TEACHER_CONSENT: ConsentDefinition = {
  code: "third_party_data_processing",
  version: V1,
  required: true,
  summary:
    "Согласие педагога на обработку его персональных данных получено, и я подтверждаю его предоставление.",
  text: "Я подтверждаю, что получил(а) согласие указанного педагога на обработку его персональных данных Оператором и на их предоставление организаторам мероприятий: фамилии, имени, отчества, должности (преподаваемой дисциплины), адреса электронной почты и номера телефона (при указании) — в целях подготовки и проведения фестивалей и конкурсов, включая указание педагога в заявках, протоколах результатов, программах выступлений и документах по итогам мероприятия (разделы 5, 8 и 9 Политики в отношении обработки персональных данных). Педагог вправе отозвать согласие в любое время, обратившись к Оператору по адресу support@vzlettalantov.by; отзыв влечёт прекращение обработки его персональных данных и их удаление в порядке, установленном разделами 11 и 13 Политики.",
};

/**
 * Application-level consents, keyed by the code the registration projection sends.
 *
 * The festival decides which of them it asks for; the wording is not the festival's to
 * choose. `personal_data` and `distribution` are always required — a child's data is
 * held on the representative's consent, and results are published on consent to
 * distribution — and the projection enforces that server-side.
 */
export const APPLICATION_CONSENTS: Readonly<Record<string, ConsentDefinition>> = {
  personal_data: {
    code: "personal_data",
    version: V1,
    required: true,
    summary:
      "Согласие законного представителя на обработку персональных данных участника для участия в этом мероприятии.",
    text: "Я подтверждаю наличие согласия законного представителя каждого заявленного участника на обработку его персональных данных в целях приёма и рассмотрения заявки, проверки соответствия условиям участия, приёма творческой работы и организации её оценивания жюри — в объёме, указанном в разделе 5 Политики в отношении обработки персональных данных. Без этого согласия участие в мероприятии невозможно.",
  },
  distribution: {
    code: "distribution",
    version: V1,
    required: true,
    summary:
      "Согласие на распространение персональных данных участника в протоколах результатов, программах выступлений и документах по итогам мероприятия.",
    text: "Я даю согласие на распространение персональных данных участника в общедоступных разделах Платформы: фамилии и имени участника (либо наименования творческого коллектива), жанра, номинации и возрастной категории, наименования учреждения, фамилии и имени педагога, наименования творческой работы и полученной награды — в протоколе результатов, программе выступлений и на странице проверки подлинности документа по итогам мероприятия. Дата рождения, адрес, контактные данные и сведения об оплате в общедоступных разделах не размещаются. Порядок прекращения распространения установлен пунктом 8.6 Политики.",
  },
  media: {
    code: "media",
    version: V1,
    required: false,
    summary:
      "Согласие на фото- и видеосъёмку участника во время мероприятия и на использование полученных материалов для освещения мероприятия.",
    text: "Я даю согласие на фото- и видеосъёмку участника во время проведения мероприятия и на использование полученных изображений и записей для освещения мероприятия организатором, включая размещение в информационных материалах о мероприятии. Согласие может быть отозвано в порядке, установленном разделом 13 Политики.",
  },
  regulations: {
    code: "regulations",
    version: V1,
    required: false,
    summary: "Я ознакомлен(а) с положением мероприятия и принимаю его условия.",
    text: "Я подтверждаю, что ознакомлен(а) с положением (регламентом) мероприятия, включая требования к творческим работам, порядок оценивания, сроки и условия оплаты участия, и принимаю его условия.",
  },
  work_publication: {
    code: "work_publication",
    version: V1,
    required: false,
    summary:
      "Согласие на публикацию творческой работы участника в открытом доступе. Отказ не влияет на участие и оценивание.",
    text: "Я даю согласие на размещение творческой работы участника в общедоступных разделах Платформы. При отсутствии этого согласия доступ к творческой работе предоставляется только организатору мероприятия и жюри (с указанием псевдонима участника), а участие в мероприятии и оценивание работы производятся в полном объёме (пункт 8.5 Политики).",
  },
};

/** The catalogue entry for an application consent code, when the platform knows it. */
export function applicationConsent(code: string): ConsentDefinition | undefined {
  return APPLICATION_CONSENTS[code];
}
