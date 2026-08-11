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
 *
 * Not everything here is a consent. The account's own data rests on the
 * Пользовательское соглашение (`docs/legal/LEGAL-003-terms-of-service.md`), a contract
 * the person enters at registration — so that box is an *acceptance*, recorded the same
 * way and withdrawn differently. `kind` says which of the two an entry is.
 */

import { ROUTES } from "@/shared/config";

/** One `(code, version)` pair as it lands in the journal. */
export type ConsentRecord = {
  readonly code: string;
  readonly version: string;
};

/** A published document a checkbox rests on, linked beside it so it can be read first. */
export type ConsentDocument = {
  /** Route of the published page. */
  readonly to: string;
  /** How the link is named. */
  readonly title: string;
};

/** A consent as the platform asks for it and records it. */
export type ConsentDefinition = {
  /** Wire code: what the journal stores as `consentType`. */
  readonly code: string;
  /** Version of *this text*. New wording, new version — never an in-place edit. */
  readonly version: string;
  /** Whether the flow may proceed without it. */
  readonly required: boolean;
  /**
   * Whether ticking this box gives a permission, or accepts a document.
   *
   * The distinction is not cosmetic: an `acceptance` may not be withdrawn the way a
   * consent may (withdrawing the agreement is ending it — see LEGAL-001 §13.7), and the
   * cabinet has to offer the honest action for each.
   */
  readonly kind: "consent" | "acceptance";
  /** The one-line statement beside the checkbox. */
  readonly summary: string;
  /** The full wording, disclosed on request beneath the checkbox. */
  readonly text: string;
  /**
   * The journal entries this one tick produces, when it stands for more than its own.
   *
   * Only the agreement checkbox uses it: what that box states is that the agreement is
   * accepted *and* the policy has been read, which are two entries and one decision by
   * the person. Each entry carries the version of the document it is about, not the
   * version of the checkbox wording — so a stored `privacy_policy` row names the policy
   * revision that was actually in force.
   */
  readonly records?: readonly ConsentRecord[];
  /** Documents to link beside the checkbox; defaults to the privacy policy. */
  readonly documents?: readonly ConsentDocument[];
};

/**
 * The `(code, version)` entries one tick of `consent` writes to the journal.
 *
 * Every caller that records a consent goes through here, so the codes and versions
 * stored are the catalogue's and never a second list that can drift from it.
 */
export function consentRecords(consent: ConsentDefinition): readonly ConsentRecord[] {
  return consent.records ?? [{ code: consent.code, version: consent.version }];
}

/** Current version of every consent text below. Bump per text, not globally. */
const V1 = "1.0";

/**
 * The wording of the agreement checkbox.
 *
 * `2.0` because `1.0` of this box said "я принимаю условия использования Платформы" at a
 * time when no such document was published — it accepted terms that existed only as a
 * phrase. Version `2.0` accepts LEGAL-003 revision 1.0, an actual contract, and the two
 * must be distinguishable in the journal.
 */
const TERMS_V2 = "2.0";

/** Revision of the published privacy policy this wording acknowledges (LEGAL-001). */
const PRIVACY_POLICY_REVISION = "1.1";

/** The published documents, as the checkboxes link them. */
const TERMS_DOCUMENT: ConsentDocument = {
  to: ROUTES.termsOfService,
  title: "Пользовательское соглашение",
};
const PRIVACY_POLICY_DOCUMENT: ConsentDocument = {
  to: ROUTES.privacyPolicy,
  title: "Политика в отношении обработки персональных данных",
};
const COOKIES_POLICY_DOCUMENT: ConsentDocument = {
  to: ROUTES.cookiesPolicy,
  title: "Политика использования файлов cookie",
};

/**
 * What registration asks for: acceptance of the agreement, and the newsletter.
 *
 * The account's own data is processed to perform the Пользовательское соглашение — a
 * contract the person enters, which art. 6 of Law 99-З makes a legal basis in its own
 * right (LEGAL-001 §4.4). So registration asks the person to *accept a document*, not to
 * consent to being processed: a consent that must be given for the service to work at
 * all would not be freely given, and asking for one the law does not require invites the
 * person to withdraw something the account cannot exist without.
 *
 * The newsletter stays a consent, separate and optional, exactly as it was: it is not
 * needed to perform the agreement, so nothing but consent can carry it (§4.3).
 */
export const ACCOUNT_CONSENTS: readonly ConsentDefinition[] = [
  {
    code: "terms_of_service",
    version: TERMS_V2,
    required: true,
    kind: "acceptance",
    records: [
      { code: "terms_of_service", version: TERMS_V2 },
      { code: "privacy_policy", version: PRIVACY_POLICY_REVISION },
    ],
    documents: [TERMS_DOCUMENT, PRIVACY_POLICY_DOCUMENT, COOKIES_POLICY_DOCUMENT],
    summary:
      "Я принимаю Пользовательское соглашение и подтверждаю, что ознакомлен(а) с Политикой в отношении обработки персональных данных и Политикой использования файлов cookie.",
    text: "Я принимаю Пользовательское соглашение, заключаемое с Оператором — Скориком Ильёй Андреевичем (УНП AE9395951), — и подтверждаю, что ознакомлен(а) с Политикой в отношении обработки персональных данных и Политикой использования файлов cookie, включая сведения об Операторе, целях и правовых основаниях обработки, сроках хранения персональных данных и порядке реализации моих прав, установленном разделом 15 Политики. Мои персональные данные — фамилия, имя, отчество (при указании), адрес электронной почты, номер телефона (при указании), сведения об учреждении и должности, сведения об учётной записи и сеансах работы — обрабатываются в целях заключения и исполнения Пользовательского соглашения: регистрации и обслуживания учётной записи, аутентификации, разграничения прав доступа, подтверждения контактных данных и направления уведомлений, связанных с оказанием услуг. Правовым основанием такой обработки является Пользовательское соглашение (статья 6 Закона; пункт 4.4 Политики), поэтому отдельное согласие на неё не запрашивается. Соглашение может быть прекращено в любое время — удалением учётной записи в личном кабинете либо заявлением на адрес support@vzlettalantov.by; обработка персональных данных при этом прекращается, а данные удаляются в порядке, установленном разделами 11 и 13 Политики, за исключением данных, хранение которых предусмотрено законодательством.",
  },
  {
    code: "marketing",
    version: V1,
    required: false,
    kind: "consent",
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
  kind: "consent",
  summary:
    "Согласие законного представителя участника на обработку его персональных данных получено, и я подтверждаю его предоставление.",
  text: "Я подтверждаю, что являюсь законным представителем участника либо располагаю согласием его законного представителя на обработку персональных данных участника, и даю (подтверждаю) согласие на обработку персональных данных участника: фамилии, имени, отчества, даты рождения (для определения возрастной категории), изображения (фотографии) участника, сведений об учреждении, коллективе и педагоге, сведений о заявках, творческих работах и результатах их оценивания — в объёме, указанном в разделе 5 Политики в отношении обработки персональных данных, в целях участия в фестивалях и конкурсах, проводимых на Платформе. Творческая работа передаётся жюри с указанием псевдонима участника. Согласие может быть отозвано в любое время; отзыв влечёт прекращение обработки персональных данных участника, их удаление и невозможность дальнейшего участия в мероприятии (разделы 6 и 13 Политики).",
};

/**
 * The consent that authorises holding an adult participant's data.
 *
 * A participant of eighteen or over consents for themselves — nobody represents them
 * (LEGAL-001 §6.2). But the platform never speaks to them at the moment their record is
 * entered, exactly as with a teacher, so the statement made here is the same one §5.4 of
 * the policy requires of whoever enters another person's data: their consent has already
 * been obtained.
 *
 * It carries its own code rather than sharing the teacher's `third_party_data_processing`,
 * though the statement is word for word the same kind. What the two authorise is not the
 * same: with one type, a consent recorded while adding a teacher would pass the check
 * that guards a participant's record, and the journal could not say which person any
 * entry was about.
 */
export const ADULT_PARTICIPANT_CONSENT: ConsentDefinition = {
  code: "participant_data_processing",
  version: V1,
  required: true,
  kind: "consent",
  summary:
    "Согласие участника на обработку его персональных данных получено, и я подтверждаю его предоставление.",
  text: "Я подтверждаю, что получил(а) согласие указанного участника на обработку его персональных данных Оператором и на их предоставление организаторам мероприятий: фамилии, имени, отчества, даты рождения (для определения возрастной категории), изображения (фотографии) участника, сведений об учреждении, коллективе и педагоге, сведений о заявках, творческих работах и результатах их оценивания — в объёме, указанном в разделе 5 Политики в отношении обработки персональных данных, в целях участия в фестивалях и конкурсах, проводимых на Платформе. Творческая работа передаётся жюри с указанием псевдонима участника. Участник вправе отозвать согласие в любое время, обратившись к Оператору по адресу support@vzlettalantov.by; отзыв влечёт прекращение обработки его персональных данных, их удаление и невозможность дальнейшего участия в мероприятии (разделы 6, 11 и 13 Политики).",
};

/** The age from which a participant consents for themselves (LEGAL-001 §6.2). */
const ADULT_AGE = 18;

/**
 * Age in whole years on `on`, or `null` when the date is missing or unreadable.
 *
 * The ISO string is taken apart rather than fed to `new Date`, which reads a bare
 * `YYYY-MM-DD` as UTC midnight and then reports its parts in local time — west of
 * Greenwich that is the previous day, which on a birthday is a whole year.
 */
function ageInYears(birthDate: string | null | undefined, on: Date): number | null {
  const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec((birthDate ?? "").trim());
  if (parts == null) {
    return null;
  }
  const [year, month, day] = [Number(parts[1]), Number(parts[2]), Number(parts[3])];
  const beforeBirthday =
    on.getMonth() + 1 < month || (on.getMonth() + 1 === month && on.getDate() < day);
  return on.getFullYear() - year - (beforeBirthday ? 1 : 0);
}

/**
 * Which consent authorises holding this participant's data — theirs, or their
 * representative's.
 *
 * An adult's record held on a "I am the legal representative" consent rests on a
 * statement that was never true, so the choice follows the participant's own age rather
 * than one wording being made to cover everybody (LEGAL-001 §6.2).
 *
 * Two cases fall back to the representative's consent, both deliberately: a collective,
 * whose row is not a person and any of whose members may be a child, and a birth date
 * that is missing or unreadable, where the stricter basis is the safe one.
 */
export function participantConsent(participant: {
  readonly birthDate?: string | null;
  readonly participantType?: string | null;
  /** Reference date for the age; defaults to today. Injected by the tests. */
  readonly on?: Date;
}): ConsentDefinition {
  if ((participant.participantType ?? "solo") === "collective") {
    return PARTICIPANT_CONSENT;
  }
  const age = ageInYears(participant.birthDate, participant.on ?? new Date());
  return age != null && age >= ADULT_AGE ? ADULT_PARTICIPANT_CONSENT : PARTICIPANT_CONSENT;
}

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
  kind: "consent",
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
    kind: "consent",
    summary:
      "Согласие законного представителя на обработку персональных данных участника для участия в этом мероприятии.",
    text: "Я подтверждаю наличие согласия законного представителя каждого заявленного участника на обработку его персональных данных в целях приёма и рассмотрения заявки, проверки соответствия условиям участия, приёма творческой работы и организации её оценивания жюри — в объёме, указанном в разделе 5 Политики в отношении обработки персональных данных. Без этого согласия участие в мероприятии невозможно.",
  },
  distribution: {
    code: "distribution",
    version: V1,
    required: true,
    kind: "consent",
    summary:
      "Согласие на распространение персональных данных участника в протоколах результатов, программах выступлений и документах по итогам мероприятия.",
    text: "Я даю согласие на распространение персональных данных участника в общедоступных разделах Платформы: фамилии и имени участника (либо наименования творческого коллектива), жанра, номинации и возрастной категории, наименования учреждения, фамилии и имени педагога, наименования творческой работы и полученной награды — в протоколе результатов, программе выступлений и на странице проверки подлинности документа по итогам мероприятия. Дата рождения, адрес, контактные данные и сведения об оплате в общедоступных разделах не размещаются. Порядок прекращения распространения установлен пунктом 8.6 Политики.",
  },
  media: {
    code: "media",
    version: V1,
    required: false,
    kind: "consent",
    summary:
      "Согласие на фото- и видеосъёмку участника во время мероприятия и на использование полученных материалов для освещения мероприятия.",
    text: "Я даю согласие на фото- и видеосъёмку участника во время проведения мероприятия и на использование полученных изображений и записей для освещения мероприятия организатором, включая размещение в информационных материалах о мероприятии. Согласие может быть отозвано в порядке, установленном разделом 13 Политики.",
  },
  regulations: {
    code: "regulations",
    version: V1,
    required: false,
    kind: "consent",
    summary: "Я ознакомлен(а) с положением мероприятия и принимаю его условия.",
    text: "Я подтверждаю, что ознакомлен(а) с положением (регламентом) мероприятия, включая требования к творческим работам, порядок оценивания, сроки и условия оплаты участия, и принимаю его условия.",
  },
  work_publication: {
    code: "work_publication",
    version: V1,
    required: false,
    kind: "consent",
    summary:
      "Согласие на публикацию творческой работы участника в открытом доступе. Отказ не влияет на участие и оценивание.",
    text: "Я даю согласие на размещение творческой работы участника в общедоступных разделах Платформы. При отсутствии этого согласия доступ к творческой работе предоставляется только организатору мероприятия и жюри (с указанием псевдонима участника), а участие в мероприятии и оценивание работы производятся в полном объёме (пункт 8.5 Политики).",
  },
};

/** The catalogue entry for an application consent code, when the platform knows it. */
export function applicationConsent(code: string): ConsentDefinition | undefined {
  return APPLICATION_CONSENTS[code];
}
