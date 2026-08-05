/**
 * `/cookies` — the cookie policy, an annex to the personal-data policy.
 *
 * Source of truth: `docs/legal/LEGAL-002-cookies-policy.md`; numbering matches it.
 *
 * Two tables here describe running code and go stale first: §3 mirrors
 * `REFRESH_TOKEN_COOKIE` / `SIMPLE_JWT` in the backend settings, and §5 mirrors the
 * browser-storage keys in `shared/constants` and the competition drafts. §2 states
 * that nothing analytic loads before consent — a promise kept by
 * `features/cookie-consent`, not by this text.
 */

import { ROUTES } from "@/shared/config";
import { useSeo } from "@/shared/seo";
import {
  LegalCell,
  LegalClause,
  LegalDocument,
  type LegalFact,
  LegalList,
  LegalMail,
  LegalParagraph,
  LegalRow,
  LegalSection,
  LegalTable,
  type LegalTocEntry,
  LegalToken,
} from "./legal-document";
import { COOKIES_POLICY_REVISION, LEGAL_OPERATOR } from "./legal-facts";

const TOC: readonly LegalTocEntry[] = [
  { id: "obshchie-polozheniya", title: "Общие положения" },
  { id: "osnovaniya", title: "Правовые основания и порядок получения согласия" },
  { id: "neobhodimye", title: "Строго необходимые файлы cookie" },
  { id: "analiticheskie", title: "Аналитические файлы cookie" },
  { id: "brauzer", title: "Данные, сохраняемые в браузере" },
  { id: "vstroennye", title: "Файлы cookie встроенных документов" },
  { id: "upravlenie", title: "Порядок управления файлами cookie" },
  { id: "aktualizaciya", title: "Порядок актуализации. Контактные данные" },
];

function facts(): readonly LegalFact[] {
  const items: LegalFact[] = [
    { label: "Оператор", value: `${LEGAL_OPERATOR.name}, УНП ${LEGAL_OPERATOR.unp}` },
    { label: "Адрес электронной почты", value: <LegalMail address={LEGAL_OPERATOR.email} /> },
  ];
  if (LEGAL_OPERATOR.postalAddress != null) {
    items.push({ label: "Адрес для обращений", value: LEGAL_OPERATOR.postalAddress });
  }
  return items;
}

export function CookiesPolicyPage(): React.JSX.Element {
  useSeo({
    title: "Политика использования cookies",
    description:
      "Состав применяемых на платформе «Взлёт талантов» файлов cookie, цели и сроки их использования, порядок управления ими. Аналитические файлы cookie применяются после получения согласия.",
  });

  return (
    <LegalDocument
      eyebrow="Правовые документы"
      title="Политика использования файлов cookie"
      description="Политика cookie является неотъемлемой частью Политики в отношении обработки персональных данных и определяет состав применяемых файлов cookie, цели и сроки их использования, а также порядок управления ими."
      revision={COOKIES_POLICY_REVISION}
      facts={facts()}
      toc={TOC}
    >
      <LegalSection id="obshchie-polozheniya" number={1} heading="Общие положения">
        <LegalClause n="1.1">
          Настоящая Политика использования файлов cookie (далее — Политика cookie) определяет состав
          применяемых на платформе «Взлёт талантов» (далее — Платформа) файлов cookie, цели и сроки
          их использования, а также порядок управления ими.
        </LegalClause>
        <LegalClause n="1.2">
          Политика cookie является неотъемлемой частью{" "}
          <a href={ROUTES.privacyPolicy} className="font-medium text-foreground hover:underline">
            Политики в отношении обработки персональных данных
          </a>{" "}
          (далее — Основная политика). Понятия, не определённые в Политике cookie, применяются в
          значениях, определённых Основной политикой и статьёй 1 Закона Республики Беларусь от 7 мая
          2021 г. № 99-З «О защите персональных данных» (далее — Закон).
        </LegalClause>
        <LegalClause n="1.3">
          Файл cookie — небольшой текстовый файл, сохраняемый информационным ресурсом в программе
          просмотра (браузере) субъекта персональных данных и передаваемый обратно этому ресурсу при
          последующих обращениях.
        </LegalClause>
        <LegalClause n="1.4">На Платформе применяются две категории файлов cookie:</LegalClause>
        <LegalList>
          <li>
            <strong>строго необходимые</strong> — обеспечивающие аутентификацию и безопасность
            сеанса работы; устанавливаются без получения предварительного согласия (раздел 3);
          </li>
          <li>
            <strong>аналитические</strong> — обеспечивающие сбор статистических сведений о посещении
            Платформы; устанавливаются исключительно после получения согласия субъекта персональных
            данных (раздел 4).
          </li>
        </LegalList>
      </LegalSection>

      <LegalSection
        id="osnovaniya"
        number={2}
        heading="Правовые основания и порядок получения согласия"
      >
        <LegalClause n="2.1">
          Правовым основанием использования строго необходимых файлов cookie является обработка
          персональных данных в целях заключения и исполнения договора, стороной которого является
          субъект персональных данных, а также исполнение Оператором обязанности по обеспечению
          защиты информации (статья 6 Закона). Без указанных файлов cookie оказание услуг, связанных
          с использованием личного кабинета, невозможно.
        </LegalClause>
        <LegalClause n="2.2">
          Правовым основанием использования аналитических файлов cookie является согласие субъекта
          персональных данных (статья 5 Закона), а в части трансграничной передачи — согласие
          субъекта персональных данных, предусмотренное статьёй 9 Закона.
        </LegalClause>
        <LegalClause n="2.3">
          Согласие на использование аналитических файлов cookie запрашивается при первом посещении
          Платформы посредством отдельного элемента интерфейса, содержащего равнозначные по
          доступности и расположению элементы управления «Принять все» и «Принять только
          необходимые». Отказ от предоставления согласия совершается одним действием, как и его
          предоставление.
        </LegalClause>
        <LegalClause n="2.4">
          До получения согласия программные компоненты сервисов статистики не загружаются и передача
          данных не осуществляется.
        </LegalClause>
        <LegalClause n="2.5">
          Продолжение использования Платформы, прокрутка страницы либо закрытие указанного элемента
          интерфейса согласием не признаются.
        </LegalClause>
        <LegalClause n="2.6">
          Согласие может быть отозвано в любое время посредством элемента управления «Настройки
          cookie», размещённого в нижней части страниц Платформы. Отзыв согласия влечёт прекращение
          использования аналитических файлов cookie; ранее собранные сервисом статистики сведения
          удаляются в соответствии с правилами такого сервиса.
        </LegalClause>
        <LegalClause n="2.7">
          Отказ от предоставления согласия на использование аналитических файлов cookie либо его
          отзыв не влекут ограничения доступа к Платформе и её функциям.
        </LegalClause>
      </LegalSection>

      <LegalSection id="neobhodimye" number={3} heading="Строго необходимые файлы cookie">
        <LegalTable headers={["Наименование", "Назначение", "Срок хранения", "Параметры"]}>
          <LegalRow>
            <LegalCell emphasis>
              <LegalToken>refresh_token</LegalToken>
            </LegalCell>
            <LegalCell>
              Хранение маркера продления сеанса работы, обеспечивающего продолжение работы в личном
              кабинете без повторного ввода пароля
            </LegalCell>
            <LegalCell>14 дней</LegalCell>
            <LegalCell>
              <LegalToken>HttpOnly</LegalToken> (недоступен сценариям на стороне браузера),{" "}
              <LegalToken>Secure</LegalToken> (передаётся только по защищённому соединению),{" "}
              <LegalToken>SameSite=Strict</LegalToken> (не передаётся при переходах со сторонних
              ресурсов), ограничен адресом <LegalToken>/api/v1/auth</LegalToken>
            </LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>
              <LegalToken>csrftoken</LegalToken>
            </LegalCell>
            <LegalCell>
              Защита форм служебных разделов Платформы от подделки межсайтовых запросов (CSRF)
            </LegalCell>
            <LegalCell>до 1 года</LegalCell>
            <LegalCell>
              <LegalToken>Secure</LegalToken>
            </LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>
              <LegalToken>sessionid</LegalToken>
            </LegalCell>
            <LegalCell>Обеспечение сеанса работы в интерфейсе администрирования</LegalCell>
            <LegalCell>до 14 дней</LegalCell>
            <LegalCell>
              <LegalToken>HttpOnly</LegalToken>, <LegalToken>Secure</LegalToken>,{" "}
              <LegalToken>SameSite=Lax</LegalToken>
            </LegalCell>
          </LegalRow>
        </LegalTable>
        <LegalClause n="3.2">
          Маркер доступа, применяемый при обращении Платформы к её программному интерфейсу, имеет
          срок действия пятнадцать минут и сохраняется исключительно в памяти открытой страницы.
        </LegalClause>
        <LegalClause n="3.3">
          Сведения о сеансе работы, связанном с файлом cookie <LegalToken>refresh_token</LegalToken>{" "}
          (дата начала, дата последней активности, IP-адрес, обозначение устройства), обрабатываются
          как персональные данные в порядке, установленном разделами 5 и 11{" "}
          <a href={ROUTES.privacyPolicy} className="font-medium text-foreground hover:underline">
            Основной политики
          </a>
          . Завершение работы в личном кабинете влечёт удаление указанного файла cookie и
          прекращение сеанса работы.
        </LegalClause>
      </LegalSection>

      <LegalSection id="analiticheskie" number={4} heading="Аналитические файлы cookie">
        <LegalClause n="4.1">
          При наличии согласия субъекта персональных данных на Платформе применяются сервисы
          статистики «Яндекс Метрика» (ООО «ЯНДЕКС») и Google Analytics (Google LLC) и
          устанавливаются следующие файлы cookie:
        </LegalClause>
        <LegalTable headers={["Сервис", "Наименование", "Назначение", "Срок хранения"]}>
          <LegalRow>
            <LegalCell emphasis>«Яндекс Метрика»</LegalCell>
            <LegalCell>
              <LegalToken>_ym_uid</LegalToken>
            </LegalCell>
            <LegalCell>Идентификатор программы просмотра (браузера)</LegalCell>
            <LegalCell>до 1 года</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>«Яндекс Метрика»</LegalCell>
            <LegalCell>
              <LegalToken>_ym_d</LegalToken>
            </LegalCell>
            <LegalCell>Дата первого посещения Платформы</LegalCell>
            <LegalCell>до 1 года</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>«Яндекс Метрика»</LegalCell>
            <LegalCell>
              <LegalToken>ymex</LegalToken>
            </LegalCell>
            <LegalCell>Служебные сведения сервиса</LegalCell>
            <LegalCell>до 1 года</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>«Яндекс Метрика»</LegalCell>
            <LegalCell>
              <LegalToken>_ym_isad</LegalToken>
            </LegalCell>
            <LegalCell>Сведения о применении средств блокировки рекламы</LegalCell>
            <LegalCell>2 дня</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>«Яндекс Метрика»</LegalCell>
            <LegalCell>
              <LegalToken>_ym_visorc</LegalToken>
            </LegalCell>
            <LegalCell>Обеспечение записи действий на странице</LegalCell>
            <LegalCell>30 минут</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>Google Analytics</LegalCell>
            <LegalCell>
              <LegalToken>_ga</LegalToken>
            </LegalCell>
            <LegalCell>Идентификатор программы просмотра (браузера)</LegalCell>
            <LegalCell>до 2 лет</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>Google Analytics</LegalCell>
            <LegalCell>
              <LegalToken>_ga_&lt;код потока данных&gt;</LegalToken>
            </LegalCell>
            <LegalCell>Состояние сеанса работы</LegalCell>
            <LegalCell>до 2 лет</LegalCell>
          </LegalRow>
        </LegalTable>
        <LegalParagraph>
          Состав файлов cookie определяется указанными сервисами; актуальный перечень размещается в
          их документации.
        </LegalParagraph>
        <LegalClause n="4.2">
          Посредством аналитических файлов cookie обрабатываются сведения о посещении Платформы:
          адреса просмотренных страниц, источник перехода, тип устройства и программы просмотра,
          язык, приблизительное местоположение, определённое по IP-адресу, идентификатор программы
          просмотра.
        </LegalClause>
        <LegalClause n="4.3">
          Сервисам статистики предоставляются исключительно сведения, перечисленные в пункте 4.2.
        </LegalClause>
        <LegalClause n="4.4">
          Использование аналитических файлов cookie влечёт трансграничную передачу указанных
          сведений: сервисом «Яндекс Метрика» — в Российскую Федерацию, сервисом Google Analytics —
          в Соединённые Штаты Америки и иные государства размещения инфраструктуры Google LLC.
          Передача осуществляется исключительно при наличии согласия субъекта персональных данных и
          прекращается при его отзыве.
        </LegalClause>
        <LegalClause n="4.5">
          Сведения, полученные посредством аналитических файлов cookie, используются в целях оценки
          посещаемости Платформы и удобства её разделов.
        </LegalClause>
      </LegalSection>

      <LegalSection id="brauzer" number={5} heading="Данные, сохраняемые в браузере">
        <LegalClause n="5.1">
          Помимо файлов cookie Платформа сохраняет в локальном хранилище программы просмотра (
          <LegalToken>localStorage</LegalToken>, <LegalToken>sessionStorage</LegalToken>) следующие
          записи. Указанные записи на сервер Платформы не передаются.
        </LegalClause>
        <LegalTable headers={["Ключ", "Хранилище", "Назначение", "Срок хранения"]}>
          <LegalRow>
            <LegalCell emphasis>
              <LegalToken>vt-cookie-consent</LegalToken>
            </LegalCell>
            <LegalCell>localStorage</LegalCell>
            <LegalCell>
              Сведения о решении субъекта персональных данных в отношении аналитических файлов
              cookie и дата его принятия
            </LegalCell>
            <LegalCell>1 год, после чего согласие запрашивается повторно</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>
              <LegalToken>vt-theme</LegalToken>
            </LegalCell>
            <LegalCell>localStorage</LegalCell>
            <LegalCell>Выбранная тема оформления интерфейса</LegalCell>
            <LegalCell>До удаления субъектом персональных данных</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>
              <LegalToken>vt-sidebar-collapsed</LegalToken>
            </LegalCell>
            <LegalCell>localStorage</LegalCell>
            <LegalCell>Состояние боковой панели интерфейса</LegalCell>
            <LegalCell>До удаления субъектом персональных данных</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>
              <LegalToken>vt:organizer-id</LegalToken>
            </LegalCell>
            <LegalCell>sessionStorage</LegalCell>
            <LegalCell>
              Организатор мероприятия, в контексте которого выполняется работа в служебном
              интерфейсе
            </LegalCell>
            <LegalCell>До закрытия вкладки браузера</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>
              <LegalToken>competition-regulation-draft:…</LegalToken>,{" "}
              <LegalToken>competition-regulation-notes:…</LegalToken>
            </LegalCell>
            <LegalCell>sessionStorage</LegalCell>
            <LegalCell>
              Черновик регламента мероприятия, обеспечивающий сохранность несохранённых сведений при
              обновлении страницы
            </LegalCell>
            <LegalCell>До закрытия вкладки браузера</LegalCell>
          </LegalRow>
        </LegalTable>
      </LegalSection>

      <LegalSection
        id="vstroennye"
        number={6}
        heading="Файлы cookie при просмотре встроенных документов"
      >
        <LegalClause n="6.1">
          При размещении организатором мероприятия регламента либо иного документа в виде ссылки на
          внешний информационный ресурс (в том числе Google Docs, Google Drive) содержимое документа
          отображается непосредственно с серверов соответствующего ресурса. Обращение программы
          просмотра к такому ресурсу производится напрямую; владелец ресурса вправе устанавливать
          собственные файлы cookie и обрабатывать данные посетителя как самостоятельный оператор в
          соответствии со своими правилами. Оператор доступа к таким файлам cookie не имеет.
        </LegalClause>
        <LegalClause n="6.2">
          Субъект персональных данных вправе воздержаться от открытия раздела со встроенным
          документом, ограничить установку сторонних файлов cookie средствами программы просмотра
          либо использовать режим приватного просмотра.
        </LegalClause>
      </LegalSection>

      <LegalSection id="upravlenie" number={7} heading="Порядок управления файлами cookie">
        <LegalClause n="7.1">
          Управление согласием на использование аналитических файлов cookie осуществляется
          посредством элемента управления «Настройки cookie», размещённого в нижней части страниц
          Платформы.
        </LegalClause>
        <LegalClause n="7.2">
          Удаление и ограничение установки файлов cookie осуществляются средствами программы
          просмотра:
        </LegalClause>
        <LegalTable headers={["Программа просмотра", "Раздел настроек"]}>
          <LegalRow>
            <LegalCell emphasis>Google Chrome</LegalCell>
            <LegalCell>
              Настройки → Конфиденциальность и безопасность → Файлы cookie и другие данные сайтов
            </LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>Mozilla Firefox</LegalCell>
            <LegalCell>Настройки → Приватность и защита → Куки и данные сайтов</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>Microsoft Edge</LegalCell>
            <LegalCell>Настройки → Файлы cookie и разрешения сайтов</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>Safari (macOS)</LegalCell>
            <LegalCell>Настройки → Конфиденциальность → Управлять данными веб-сайтов</LegalCell>
          </LegalRow>
          <LegalRow>
            <LegalCell emphasis>Safari (iOS, iPadOS)</LegalCell>
            <LegalCell>Настройки → Safari → Дополнения → Данные сайтов</LegalCell>
          </LegalRow>
        </LegalTable>
        <LegalClause n="7.3">
          Ограничение установки строго необходимых файлов cookie влечёт невозможность аутентификации
          и работы в личном кабинете, а также отклонение отправляемых форм служебных разделов.
          Доступ к общедоступным разделам Платформы сохраняется.
        </LegalClause>
        <LegalClause n="7.4">
          Удаление записей локального хранилища, указанных в разделе 5, влечёт сброс настроек
          интерфейса и утрату несохранённых черновиков.
        </LegalClause>
      </LegalSection>

      <LegalSection id="aktualizaciya" number={8} heading="Порядок актуализации. Контактные данные">
        <LegalClause n="8.1">
          Оператор вправе вносить изменения в Политику cookie, в том числе при изменении состава
          применяемых файлов cookie. Новая редакция вступает в силу со дня её размещения по адресу
          https://{LEGAL_OPERATOR.siteHost}
          {ROUTES.cookiesPolicy}.
        </LegalClause>
        <LegalClause n="8.2">
          При подключении информационного ресурса, устанавливающего файлы cookie, не отнесённые к
          строго необходимым, Политика cookie дополняется соответствующими сведениями, а согласие
          субъекта персональных данных запрашивается до начала использования таких файлов cookie.
        </LegalClause>
        <LegalClause n="8.3">
          Обращения по вопросам использования файлов cookie и заявления о реализации прав субъекта
          персональных данных направляются на адрес электронной почты{" "}
          <LegalMail address={LEGAL_OPERATOR.email} />. Порядок рассмотрения заявлений и сроки
          установлены разделом 15{" "}
          <a href={ROUTES.privacyPolicy} className="font-medium text-foreground hover:underline">
            Основной политики
          </a>
          .
        </LegalClause>
      </LegalSection>
    </LegalDocument>
  );
}
