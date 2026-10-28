import {
  APP_NAME,
  CONTACT_PERSON,
  CONTACT_PHONE,
  CONTACT_PHONE_HREF,
  CONTACT_TELEGRAM,
  CONTACT_TELEGRAM_HREF,
  ROUTES,
  SUPPORT_EMAIL,
} from "@/shared/config";
import { cn } from "@/shared/lib";
import { absoluteUrl, useSeo } from "@/shared/seo";
import { PageContainer } from "@/shared/ui";

/**
 * `/organizers` — what the platform does for the person running a festival.
 *
 * The page sent to an organizer after the first call, so it is written for one
 * reader on one phone: the festival's own year in order — приём заявок, разбор
 * заявок, программа, день фестиваля, итоги — with a screen beside each claim.
 * Public and indexed, unlike the programme and the protocol: this one is *meant*
 * to be found.
 *
 * It lives here rather than on a slide deck or somebody else's hosting for the
 * same reason the festival's own page does: a link that is handed out survives
 * longer than the conversation that produced it, and it has to keep working when
 * the product moves on. Rebuilt with the deploy, so it can never describe a
 * version of the platform that no longer exists.
 *
 * Every screenshot comes from a demo festival with invented participants — the
 * live one is full of children's names, their schools and their teachers'
 * phone numbers, and none of that belongs in a sales page.
 */
export function OrganizersPage(): React.JSX.Element {
  useSeo({
    title: "Организаторам фестивалей",
    description:
      "Платформа для организаторов детских творческих фестивалей: приём заявок, разбор заявок, программа выступлений, судейство, протокол и дипломы в одном месте.",
    image: absoluteUrl("/organizers/program.webp"),
    imageAlt: "Конструктор программы фестиваля на платформе «Взлёт талантов»",
    canonicalPath: ROUTES.organizers,
    // Закрыта от индексации, пока на ней напечатан личный телефон: страницу
    // рассылают ссылкой, и находить её через поиск никто не должен. Это не
    // защита от сборщиков номеров — те на `noindex` не смотрят, — а решение
    // не заводить номер в поисковую выдачу. Снимается вместе с телефоном.
    robots: "noindex",
  });

  return (
    <PageContainer size="default" className="gap-12 px-4 py-10 sm:px-6 md:gap-16 md:py-16">
      <header className="flex flex-col gap-4">
        <p className="font-medium text-muted-foreground text-xs uppercase tracking-[0.18em]">
          Организаторам
        </p>
        <h1 className="max-w-3xl text-balance font-bold text-3xl text-foreground tracking-tight sm:text-4xl">
          Фестиваль целиком — от заявки до диплома
        </h1>
        <p className="max-w-2xl text-base text-muted-foreground leading-7">
          «{APP_NAME}» — платформа для организаторов детских творческих фестивалей. Приём заявок,
          разбор заявок, программа выступлений, судейство, протокол и дипломы живут в одном месте и
          знают друг о друге: номер из принятой заявки сам встаёт в программу, из программы попадает
          в протокол, из протокола — в диплом.
        </p>
        {/* Written out rather than hidden behind a button: the reader is deciding
            whether to call, and a «Связаться» that only opens a mail client
            answers a question they did not ask. */}
        <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1 pt-1 text-sm">
          <span className="text-muted-foreground">{CONTACT_PERSON}</span>
          <a
            href={CONTACT_PHONE_HREF}
            className="font-semibold text-foreground tabular-nums hover:underline"
          >
            {CONTACT_PHONE}
          </a>
          <a
            href={CONTACT_TELEGRAM_HREF}
            className="font-semibold text-foreground hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            {CONTACT_TELEGRAM}
          </a>
        </p>
      </header>

      <Stage label="Приём заявок" title="У фестиваля появляется своя страница">
        <p>
          Афиша, даты, место, положение и условия по каждому жанру — всё на одной странице, ссылку
          на которую можно давать в соцсетях и рассылках. Заявка подаётся оттуда же, без переписки и
          бумажных бланков.
        </p>
        <Points
          items={[
            [
              "Приём открывается по жанрам отдельно.",
              "У вокала одни сроки, у хореографии другие — платформа закроет каждый в своё время сама.",
            ],
            [
              "Лист ожидания,",
              "когда мест в жанре уже нет: заявка не теряется, вы переводите её в очередь, когда место освободилось.",
            ],
            [
              "В заявке сразу всё:",
              "участники, педагоги, номер и его длительность, фонограмма, видео, документы.",
            ],
            [
              "Оплата подтверждается квитанцией,",
              "которую участник прикладывает к заявке, — вы видите, кто оплатил, а кто ещё нет.",
            ],
          ]}
        />
        <Shot
          src="/organizers/festival.webp"
          width={1440}
          height={980}
          alt="Публичная страница фестиваля: афиша, даты, кнопка «Подать заявку» и сроки приёма по каждому жанру"
          caption={
            <>
              Страница фестиваля глазами участника. <b>Приём заявок открыт</b> — и по каждому жанру
              видно, до какого числа.
            </>
          }
        />
      </Stage>

      <Stage label="Подготовка" title="Заявки разбираются по очереди, а не по почте">
        <p>
          Все заявки лежат в одной очереди и разложены по состояниям: ждут оплату, готовы к
          фестивалю, отправлены на доработку, отменены. Вы берёте следующую, делаете одно действие и
          идёте дальше.
        </p>
        <Points
          items={[
            [
              "Рабочая карточка",
              "показывает заявку целиком и держит файлы под рукой — музыку, видео, документы, квитанцию.",
            ],
            [
              "Отбор по фестивалю и жанру,",
              "и сразу видно, сколько это номеров и сколько они идут по времени.",
            ],
            ["Выгрузка реестра в Excel", "и скачивание всех приложенных документов одним архивом."],
            [
              "Заморозка редактирования",
              "одной кнопкой на весь фестиваль, когда приём закрыт и состав больше менять нельзя.",
            ],
          ]}
        />
        <Shot
          src="/organizers/applications.webp"
          width={1600}
          height={1000}
          alt="Экран обработки заявок: вкладки по состояниям, список входящих заявок и рабочая карточка с действиями"
          caption={
            <>
              180 номеров в очереди и <b>10 часов 19 минут</b> выступлений — платформа считает это
              сама, пока вы разбираете заявки.
            </>
          }
        />
      </Stage>

      <Stage label="Программа" title="Программа собирается за одно нажатие">
        <p>
          Самая долгая ручная работа фестиваля. Платформа составляет порядок выступлений по вашим
          правилам: как группировать день, через сколько номеров ставить перерыв, чем открывать и
          чем закрывать. Дальше программу можно править руками — перетаскиванием.
        </p>
        <Points
          items={[
            ["Группировка по жанру, возрасту, составу", "— в том порядке, который вы выберете."],
            [
              "Повторные выходы разводятся:",
              "участник, который выступает трижды, не идёт три номера подряд.",
            ],
            [
              "Расписание по времени",
              "с буфером между номерами — видно, когда начнётся каждый номер и когда закончится отделение.",
            ],
            ["Свои колонки", "под то, чего нет во встроенных: «микрофон», «реквизит», «оплачено»."],
            [
              "Печать и выгрузка:",
              "PDF на A4, Excel, а фонограммы и видеоматериалы — одним архивом в порядке номеров.",
            ],
            [
              "Номера закрепляются за участниками",
              "после первой публикации: перестановка меняет порядок, но не номер, который человеку уже назвали.",
            ],
          ]}
        />
        <Shot
          src="/organizers/program.webp"
          width={1600}
          height={909}
          alt="Конструктор программы: список программ по жанрам, настройки буфера и начала, таблица номеров с временем"
          caption={
            <>
              45 номеров, <b>3 часа 4 минуты</b>, время у каждого выступления. Колонки на экране
              выбираете вы — организатору нужны одни, звукорежиссёру другие.
            </>
          }
        />
      </Stage>

      <Stage label="День фестиваля" title="Одна программа — своя ссылка каждому, кто работает">
        <p>
          Из готовой программы делается сколько угодно публичных ссылок, и у каждой свой набор
          колонок. Звукорежиссёру — время, номер и комментарий. Экрану у сцены — время, участник и
          номер. Ведущей — её собственная, с управлением.
        </p>
        <Points
          items={[
            [
              "Ведущая ведёт день с телефона:",
              "«на сцене», «выступил», «пропущен», «номер отменён» — и это сразу видно на всех остальных экранах.",
            ],
            [
              "Номер можно переставить на ходу,",
              "если участник не успевает: порядок поменяется, номера останутся при своих участниках.",
            ],
            [
              "Личный слой ведущей:",
              "кто уже за сценой и пометки по номеру («зовут Алиса, не Алла») — это видно только по её ссылке и больше нигде.",
            ],
            [
              "Чувствительные колонки закрыты.",
              "Телефон педагога или комментарий с «аллергия на орехи» открываются нажатием — за сценой через плечо смотрят чужие родители.",
            ],
            ["Рассылка участникам,", "когда программа опубликована: каждому его номер и время."],
          ]}
        />
        <Shot
          src="/organizers/host.webp"
          width={1340}
          height={640}
          alt="Программа ведущего: закреплённые колонки с номером и управлением, отметки «Сейчас», «За сценой», «Номер отменён», скрытые комментарии"
          caption={
            <>
              Экран ведущей. Номер слева и кнопки справа <b>не уезжают при прокрутке</b>; отменённый
              номер так и написан словами; комментарии закрыты, пока их не откроют.
            </>
          }
        />
        <Shot
          src="/organizers/stage.webp"
          width={1140}
          height={600}
          alt="Та же программа по ссылке для экрана у сцены: только время, участник и номер, без кнопок управления"
          caption={
            <>
              Та же программа, ссылка для экрана у сцены:{" "}
              <b>«Сейчас» и «Номер отменён» видят все,</b> а пометки ведущей — никто.
            </>
          }
        />
      </Stage>

      <Stage label="Дипломы" title="Свой бланк, и весь фестиваль одним нажатием">
        <p>
          Шаблон — ваш печатный бланк, на который поля ставятся мышью: имя участника, степень,
          произведение, педагог, дата, QR проверки подлинности. Дальше шаблон назначается жанрам, и
          дипломы формируются на весь фестиваль разом.
        </p>
        <Points
          items={[
            [
              "Конструктор поверх вашего PDF:",
              "бланк остаётся вашим, платформа только раскладывает по нему поля и шрифты.",
            ],
            [
              "У каждого жанра свой шаблон,",
              "а отдельной номинации можно назначить собственный — когда её судит другое жюри.",
            ],
            [
              "Благодарности педагогам",
              "считаются по-человечески: один лист на педагога, сколько бы номеров он ни выставил.",
            ],
            [
              "Диплом приходит участнику",
              "в личный кабинет, а подлинность печатного проверяется по QR-коду.",
            ],
            [
              "Если заявку исправили после выдачи",
              "— фамилию, название номера — диплом перевыпускается с тем, что в заявке написано сегодня.",
            ],
          ]}
        />
        <Shot
          src="/organizers/diploma-constructor.webp"
          width={1600}
          height={1000}
          alt="Конструктор диплома: бланк фестиваля, поле с именем участника на нём, слева список полей, справа свойства поля"
          caption={
            <>
              Ваш бланк и поля на нём. Справа видно, <b>откуда берётся значение</b> — имя участника,
              степень, педагог, — и каким шрифтом оно напечатается.
            </>
          }
        />
        <Shot
          src="/organizers/diploma-generate.webp"
          width={1600}
          height={1000}
          alt="Экран генерации дипломов: таблица по жанрам с числом выступлений и кнопка «Сформировать комплект для печати»"
          caption={
            <>
              Четыре жанра, 45 номеров в каждом — <b>180 дипломов и 24 благодарности</b> одним
              нажатием, в личные кабинеты или архивом на печать.
            </>
          }
        />
      </Stage>

      <Stage label="Зрительский приз" title="Голосование зала — по коду с афиши">
        <p>
          Зритель сканирует код, открывает список номеров и выбирает один. Без регистрации и без
          приложения. Фестиваль на платформе для этого не обязателен: список участников можно
          завести вручную или загрузить из Excel.
        </p>
        <Points
          items={[
            [
              "Участники подтягиваются из программы",
              "— с теми же номерами, которые называет ведущая со сцены.",
            ],
            [
              "Счёт показывается или прячется",
              "по вашему решению: всегда, только после завершения или никому, кроме организатора.",
            ],
            ["Табло выводится на проектор", "в зале и обновляется само, пока идёт голосование."],
          ]}
        />
        {/* Side by side, and the phone kept narrow: at equal widths a 430-pixel
            screenshot towers over a 1440-pixel one and the pair reads as a
            mistake rather than as two views of the same vote. */}
        <div className="-mx-4 flex flex-col gap-6 sm:mx-0 sm:flex-row sm:items-start md:-mx-12 lg:-mx-20">
          <Shot
            src="/organizers/vote.webp"
            width={430}
            height={860}
            bleed={false}
            className="w-full px-4 sm:w-56 sm:shrink-0 sm:px-0"
            alt="Страница голосования на телефоне: список номеров с именами участников и счётчиком голосов"
            caption="Телефон зрителя."
          />
          <Shot
            src="/organizers/board.webp"
            width={1440}
            height={860}
            bleed={false}
            className="w-full min-w-0 px-4 sm:flex-1 sm:px-0"
            alt="Табло зрительского голосования: первые места с именами участников, числом голосов и полосами"
            caption="Табло в зале — крупно, чтобы читалось с последнего ряда."
          />
        </div>
      </Stage>

      <Stage label="Итоги" title="Судейство и протокол">
        <p>
          Жюри судит онлайн по критериям, которые задаёте вы. Из оценок собирается протокол,
          протокол публикуется ссылкой — и по нему печатаются дипломы. Исправленная после публикации
          строка не остаётся незамеченной: у протокола растёт ревизия, и читатель видит, что это уже
          другая версия.
        </p>
      </Stage>

      <section className="flex flex-col gap-5">
        <h2 className="font-semibold text-foreground text-xl tracking-tight sm:text-2xl">
          Что ещё есть
        </h2>
        <ul className="grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {EXTRAS.map((extra) => (
            <li key={extra.title} className="bg-background p-4 sm:p-5">
              <p className="font-semibold text-foreground text-sm">{extra.title}</p>
              <p className="mt-1 text-muted-foreground text-sm leading-6">{extra.body}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="flex flex-col gap-4 rounded-xl border border-border bg-muted/40 p-6 sm:p-8">
        <h2 className="font-semibold text-foreground text-xl tracking-tight sm:text-2xl">
          Посмотрим на вашем фестивале
        </h2>
        <p className="max-w-2xl text-muted-foreground text-sm leading-6">
          Полчаса на звонок: заведём ваш фестиваль с вашими жанрами и возрастными категориями,
          пройдём путь от заявки до диплома на ваших же данных и посмотрим, что из этого закрывает
          вашу работу, а чего не хватает. Условия обсудим там же — они зависят от размера фестиваля.
          Звоните или пишите, в телеграме отвечаю быстрее.
        </p>
        <p className="font-semibold text-foreground text-sm">{CONTACT_PERSON}</p>
        <dl className="-mt-2 flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:gap-x-10">
          <div className="flex flex-col gap-0.5">
            <dt className="font-medium text-muted-foreground text-xs uppercase tracking-[0.14em]">
              Телефон
            </dt>
            <dd>
              <a
                href={CONTACT_PHONE_HREF}
                className="font-semibold text-base text-foreground tabular-nums hover:underline"
              >
                {CONTACT_PHONE}
              </a>
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="font-medium text-muted-foreground text-xs uppercase tracking-[0.14em]">
              Telegram
            </dt>
            <dd>
              <a
                href={CONTACT_TELEGRAM_HREF}
                className="font-semibold text-base text-foreground hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                {CONTACT_TELEGRAM}
              </a>
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="font-medium text-muted-foreground text-xs uppercase tracking-[0.14em]">
              Почта
            </dt>
            <dd>
              <a
                href={`mailto:${SUPPORT_EMAIL}`}
                className="font-semibold text-base text-foreground hover:underline"
              >
                {SUPPORT_EMAIL}
              </a>
            </dd>
          </div>
        </dl>
      </section>

      <p className="border-border border-t pt-5 text-muted-foreground text-xs leading-6">
        Снимки экрана сделаны на демонстрационном фестивале: имена участников, школы и педагоги в
        них вымышленные.
      </p>
    </PageContainer>
  );
}

/** The short list of the sections that do not need a screen of their own. */
const EXTRAS = [
  {
    title: "Отзывы",
    body: "Код на баннере — и отзывы с фестиваля собираются сами, на одну постоянную ссылку.",
  },
  {
    title: "Реестр участников",
    body: "Участники, педагоги и учреждения заведены один раз и дальше подставляются в заявки.",
  },
  {
    title: "Команда оргкомитета",
    body: "Сотрудники приглашаются по почте, и каждому открыт только свой раздел.",
  },
  {
    title: "Финансы",
    body: "Поступления и расходы фестиваля в одном журнале.",
  },
  {
    title: "Аналитика",
    body: "Цифры по приёму заявок и фестивалям — без выдуманных графиков.",
  },
  {
    title: "Уведомления",
    body: "Участник узнаёт о статусе заявки, публикации программы и выдаче диплома письмом.",
  },
] as const;

/**
 * One stage of the festival's year: its label, its claim, and whatever is under it.
 *
 * The label is the structural device, and it encodes something true — the order
 * these happen in. Numbering them would say the same thing less clearly, since a
 * reader who runs festivals already knows what follows приём заявок.
 */
function Stage({
  label,
  title,
  children,
}: {
  label: string;
  title: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-baseline gap-3">
        <span className="shrink-0 font-semibold text-primary text-xs uppercase tracking-[0.14em]">
          {label}
        </span>
        <span aria-hidden="true" className="h-px flex-1 bg-border" />
      </div>
      <h2 className="max-w-3xl text-balance font-semibold text-foreground text-xl tracking-tight sm:text-2xl">
        {title}
      </h2>
      {/* `max-w-2xl` on the prose and nothing on the figures: a screen of the
          product is looked at, a paragraph is read, and the two want different
          widths. */}
      <div className="flex max-w-2xl flex-col gap-4 text-foreground text-sm leading-6">
        {children}
      </div>
    </section>
  );
}

/** A claim in bold and the detail that earns it. */
function Points({ items }: { items: readonly (readonly [string, string])[] }): React.JSX.Element {
  return (
    <ul className="flex flex-col gap-2.5">
      {items.map(([claim, detail]) => (
        <li key={claim} className="relative pl-5 text-muted-foreground">
          <span
            aria-hidden="true"
            className="absolute top-[0.6em] left-0 size-1.5 rounded-full bg-primary/55"
          />
          <b className="font-semibold text-foreground">{claim}</b> {detail}
        </li>
      ))}
    </ul>
  );
}

/**
 * A screen of the product, wider than the column of text that introduces it.
 *
 * `width`/`height` are the file's own, so the browser keeps the space before the
 * image arrives — on a phone over a festival's wifi that is the difference
 * between a page that settles and one that jumps under the thumb.
 */
function Shot({
  src,
  alt,
  caption,
  width,
  height,
  bleed = true,
  className,
}: {
  src: string;
  alt: string;
  caption: React.ReactNode;
  width: number;
  height: number;
  /**
   * Whether this screen may hang past the text column. Off for the ones standing
   * side by side: negative margins inside a grid pull the neighbours over each
   * other, which is exactly what it looked like.
   */
  bleed?: boolean;
  className?: string;
}): React.JSX.Element {
  return (
    <figure
      className={cn("flex flex-col gap-2", bleed && "-mx-4 sm:mx-0 md:-mx-12 lg:-mx-20", className)}
    >
      <img
        src={src}
        alt={alt}
        width={width}
        height={height}
        loading="lazy"
        decoding="async"
        className="h-auto w-full border border-border bg-muted/40 sm:rounded-lg"
      />
      <figcaption
        className={cn(
          "text-muted-foreground text-xs leading-5",
          bleed && "px-4 sm:px-0 md:px-12 lg:px-20",
        )}
      >
        {caption}
      </figcaption>
    </figure>
  );
}
