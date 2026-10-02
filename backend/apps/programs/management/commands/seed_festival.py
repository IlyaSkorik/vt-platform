"""``seed_festival`` — наполнить локальную базу фестивалем, с которого есть что составлять.

Автосоставление (VT-86) нечего проверять на трёх номерах: правила становятся
видны на масштабе. Команда делает фестиваль, по которому сразу видно каждое
правило генератора, а не просто много строк:

* **Номинации и дисциплины** — чтобы было что группировать по первым двум осям.
* **Возрастные категории, названные как их называют** («7-9 лет», «10-12 лет»):
  по алфавиту они идут не в том порядке, что по возрасту, и именно это чинит
  ранжирование возрастов в генераторе.
* **Составы** (соло, дуэт, ансамбль) и **формы участия** — остальные оси.
* **Школы** — ось «организация» и колонка, по которой читают программу.
* **Повторы**: часть участников выходит два-три раза, иначе развод повторов
  просто нечему развести.
* **Заявки не в конкурсе** (черновики, отклонённые): каталог обязан их не
  пускать в программу, и это видно по тому, что их нет среди кандидатов.

Участники и школы заводятся на отдельного владельца, а не на организацию
фестиваля: в реестре организатора демо-данным делать нечего, а программе
владелец реестра безразличен — она идёт от заявки к членству напрямую.

Использование::

    python manage.py seed_festival --acts 400
    python manage.py seed_festival --acts 1200 --nominations 5 --title "Нагрузка"
    python manage.py seed_festival --list
    python manage.py seed_festival --cleanup
"""

from __future__ import annotations

import random
import uuid
from datetime import timedelta
from typing import Any, Final

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.applications.domain.value_objects import SubmissionStatus
from apps.applications.infrastructure.models.submission import SubmissionModel
from apps.competitions.infrastructure.models.competition import CompetitionModel
from apps.competitions.infrastructure.models.taxonomy import (
    AgeCategoryModel,
    CategoryModel,
    DisciplineModel,
    ParticipantGroupModel,
    ParticipationFormatModel,
)
from apps.participants.infrastructure.models import (
    EducationalOrganizationModel,
    ParticipantOrganizationMembershipModel,
    ParticipantRegistryModel,
)
from apps.programs.application.commands import CreateProgramCommand
from apps.programs.composition import build_program_service
from apps.programs.infrastructure.models import ProgramModel

#: Метка в ``settings`` фестиваля: по ней ``--cleanup`` находит всё своё и ничего
#: чужого. Демо-данные обязаны уметь исчезать целиком.
MARKER: Final = "program_seed"

#: Номинации и их дисциплины — в том виде, в каком это пишут в положении.
_NOMINATIONS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("Вокал", ("Эстрадный вокал", "Академический вокал", "Народный вокал")),
    ("Хореография", ("Классический танец", "Народный танец", "Современный танец")),
    ("Инструментальное исполнительство", ("Фортепиано", "Струнные", "Духовые")),
    ("Театр", ("Драматический спектакль", "Музыкальный театр")),
    ("Художественное слово", ("Проза", "Поэзия")),
    ("Изобразительное искусство", ("Живопись", "Графика")),
)

#: Возрастные категории: по алфавиту «10-12 лет» идёт раньше «7-9 лет», по
#: возрасту — позже. Ради этого расхождения они здесь так и названы.
_AGE_BANDS: Final[tuple[tuple[str, int, int], ...]] = (
    ("7-9 лет", 7, 9),
    ("10-12 лет", 10, 12),
    ("13-15 лет", 13, 15),
    ("16-19 лет", 16, 19),
)

#: Составы: имя, сколько человек выходит на сцену минимум и максимум.
_GROUPS: Final[tuple[tuple[str, int, int], ...]] = (
    ("Соло", 1, 1),
    ("Дуэт", 2, 2),
    ("Ансамбль", 3, 12),
)

_FORMATS: Final[tuple[str, ...]] = ("Очно", "Заочно")

_SCHOOLS: Final[tuple[str, ...]] = (
    "ДШИ №1",
    "ДШИ №3 имени Чайковского",
    "Детская музыкальная школа «Гармония»",
    "Центр творчества «Радуга»",
    "Студия эстрадного вокала «Ля-Ля»",
    "Хореографическая школа «Пируэт»",
    "Гимназия №24",
    "Дом культуры «Юность»",
)

_CITIES: Final[tuple[str, ...]] = ("Москва", "Казань", "Нижний Новгород", "Самара", "Пермь")

#: Имена двух участников обязаны различаться: программа знает участника по имени
#: и только по нему, так что два разных ребёнка с одной подписью для неё — один
#: человек, которого она примется разводить по залу. Пул строится декартовым
#: произведением (а не по модулю со сдвигом, который схлопывает его в десяток
#: сочетаний), и при переполнении фамилия получает номер: демо-данные и должны
#: быть заметны.
#:
#: Фамилии и имена разведены по роду. Это не придирка к правдоподобию: «Иванова
#: Артём» в распечатанной программе читается как ошибка платформы, и половину
#: взгляда на демо-фестиваль съест именно она.
_NAMES_F: Final[tuple[tuple[str, ...], tuple[str, ...]]] = (
    (
        "Иванова", "Смирнова", "Попова", "Лебедева", "Новикова", "Волкова", "Михайлова",
        "Николаева", "Макарова", "Ковалёва", "Семёнова", "Голубева", "Богданова",
        "Беляева", "Киселёва",
    ),
    (
        "Анна", "Мария", "Софья", "Полина", "Алиса", "Варвара", "Ева", "Вероника",
        "Арина", "Василиса", "Злата", "Милана",
    ),
)  # fmt: skip
_NAMES_M: Final[tuple[tuple[str, ...], tuple[str, ...]]] = (
    (
        "Петров", "Кузнецов", "Соколов", "Козлов", "Морозов", "Фёдоров", "Егоров",
        "Орлов", "Андреев", "Ильин", "Павлов", "Виноградов", "Воробьёв", "Комаров",
        "Щербаков",
    ),
    (
        "Дмитрий", "Иван", "Артём", "Максим", "Кирилл", "Никита", "Матвей", "Илья",
        "Тимофей", "Степан", "Фёдор", "Глеб",
    ),
)  # fmt: skip

#: Сколько номеров привозит один исполнитель — солист или коллектив. Чаще всего
#: один, кто-то два, редкий три: столько повторов и бывает, и ровно столько нужно,
#: чтобы правилу «не два номера подряд» было что разводить.
_ACTS_PER_UNIT: Final[tuple[tuple[int, int], ...]] = ((1, 70), (2, 22), (3, 8))

_TEACHER_NAMES: Final[tuple[tuple[str, str, str], ...]] = (
    ("Петрова", "Мария", "Ивановна"),
    ("Сидоров", "Павел", "Андреевич"),
    ("Громова", "Елена", "Сергеевна"),
    ("Белов", "Антон", "Юрьевич"),
    ("Зайцева", "Ольга", "Петровна"),
    ("Рябинин", "Сергей", "Львович"),
)

#: Названия номеров, из которых собираются заголовки заявок.
_TITLES: Final[tuple[str, ...]] = (
    "Катюша",
    "Калинка",
    "Journey",
    "Вальс цветов",
    "Облака",
    "Сказка о царе",
    "Весенний этюд",
    "Полёт",
    "Не отпускай",
    "Солнечный день",
    "Метель",
    "Город детства",
    "Пробуждение",
    "Серенада",
    "Зимний вечер",
    "Карусель",
)

#: Комментарии, ради которых программа и существует: то, что надо знать на сцене.
_COMMENTS: Final[tuple[str, ...]] = (
    "",
    "",
    "",
    "Фонограмма на флешке у звукорежиссёра",
    "Нужен микрофон на стойке",
    "Выход из-за кулис справа",
    "Реквизит: стул и стол",
    "Просим поставить не раньше 12:00 — поезд",
    "После номера сразу переодевание",
)

#: Статусы, в которых заявка в конкурсе не участвует. Несколько таких нужны,
#: чтобы было видно: генератор берёт не «все заявки», а только допущенные.
_NON_COMPETING: Final[tuple[str, ...]] = (
    SubmissionStatus.DRAFT.value,
    SubmissionStatus.SUBMITTED.value,
    SubmissionStatus.WAITING_PAYMENT.value,
    SubmissionStatus.CANCELLED.value,
)


class Command(BaseCommand):
    """Создать (или убрать) демо-фестиваль для проверки автосоставления."""

    help = "Наполнить базу фестивалем с выступлениями, чтобы было на чём проверять автосоставление программы."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--acts", type=int, default=300, help="Сколько допущенных выступлений завести (по умолчанию 300).")
        parser.add_argument("--nominations", type=int, default=4, help="Сколько номинаций (по умолчанию 4, максимум 6).")
        parser.add_argument("--organization", default=None, help="UUID организации-владельца. По умолчанию — та, чьих фестивалей в базе больше.")
        parser.add_argument("--title", default=None, help="Название фестиваля.")
        parser.add_argument("--seed", type=int, default=86, help="Зерно генератора случайных чисел: один и тот же seed даёт одни и те же данные.")
        parser.add_argument("--no-programs", action="store_true", help="Не заводить пустые программы под каждую номинацию.")
        parser.add_argument("--list", action="store_true", help="Показать уже засеянные фестивали и выйти.")
        parser.add_argument("--cleanup", action="store_true", help="Удалить всё, что засеяла эта команда, и выйти.")

    def handle(self, *args: Any, **options: Any) -> None:
        if options["list"]:
            self._list()
            return
        if options["cleanup"]:
            self._cleanup()
            return

        acts = int(options["acts"])
        nominations = int(options["nominations"])
        if acts < 1:
            raise CommandError("--acts должно быть больше нуля.")
        if not 1 <= nominations <= len(_NOMINATIONS):
            raise CommandError(f"--nominations от 1 до {len(_NOMINATIONS)}.")

        organization_id = self._organization(options["organization"])
        rng = random.Random(int(options["seed"]))
        self._seed(
            acts=acts,
            nominations=nominations,
            organization_id=organization_id,
            title=options["title"],
            rng=rng,
            with_programs=not options["no_programs"],
        )

    # ------------------------------------------------------------------
    # Выбор организации
    # ------------------------------------------------------------------

    def _organization(self, requested: str | None) -> uuid.UUID:
        """Чья это будет витрина.

        ``organizer_id`` фестиваля — это id организации, и список фестивалей в
        кабинете фильтруется по нему. Ошибиться тут значит засеять данные, которых
        организатор не увидит, поэтому команда либо берёт явно указанную
        организацию, либо ту, чьих фестивалей в базе больше всего, и говорит какую.
        """
        if requested is not None:
            try:
                return uuid.UUID(str(requested))
            except ValueError as exc:
                raise CommandError(f"--organization должен быть UUID, получено {requested!r}.") from exc

        owners = [str(value) for value in CompetitionModel.objects.filter(deleted_at__isnull=True).values_list("organizer_id", flat=True)]
        if owners:
            winner = max(set(owners), key=owners.count)
            self.stdout.write(f"Организация не указана — беру ту, чьих фестивалей больше: {winner}")
            return uuid.UUID(winner)

        from apps.organization.infrastructure.models import OrganizationModel

        only = list(OrganizationModel.objects.filter(deleted_at__isnull=True).values_list("id", flat=True)[:2])
        if len(only) == 1:
            self.stdout.write(f"Организация не указана — в базе она одна: {only[0]}")
            return uuid.UUID(str(only[0]))
        raise CommandError("Не могу выбрать организацию сам — укажите --organization <uuid>.")

    # ------------------------------------------------------------------
    # Посев
    # ------------------------------------------------------------------

    @transaction.atomic
    def _seed(
        self,
        *,
        acts: int,
        nominations: int,
        organization_id: uuid.UUID,
        title: str | None,
        rng: random.Random,
        with_programs: bool,
    ) -> None:
        today = timezone.now().date()
        stamp = timezone.now().strftime("%d.%m %H:%M")
        # Реестр живёт на отдельном владельце: демо-участникам нечего делать в
        # реестре организатора, а программе владелец реестра безразличен.
        registry_owner = uuid.uuid4()

        competition = CompetitionModel.objects.create(
            title=title or f"[ДЕМО {stamp}] Фестиваль для автосоставления",
            season=f"{today.year}/{today.year + 1}",
            organizer_id=organization_id,
            status="PUBLISHED",
            venue_name="Концертный зал «Юность»",
            venue_address="Москва, ул. Тестовая, 1",
            registration_start=today - timedelta(days=60),
            registration_end=today + timedelta(days=7),
            competition_start=today + timedelta(days=30),
            competition_end=today + timedelta(days=32),
            settings={MARKER: {"registryOwnerId": str(registry_owner)}},
        )

        categories, disciplines = self._taxonomy(competition, nominations)
        groups, ages = self._groups_and_ages(competition)
        formats = [
            ParticipationFormatModel.objects.create(competition=competition, name=name, sort_order=index) for index, name in enumerate(_FORMATS)
        ]
        schools = self._schools(registry_owner, stamp)

        # Сначала решаем, кто выходит на сцену и по сколько раз, и только потом
        # заводим ровно столько людей, сколько эти исполнители требуют: пул под
        # число номеров означал бы, что состав каждого коллектива берётся наугад,
        # а наугад взятые ансамбли пересекаются все со всеми.
        blueprint = self._units(groups, acts, rng)
        people = self._people(registry_owner, schools, sum(size for _, size, _ in blueprint), rng)
        units: list[tuple[ParticipantGroupModel, list[ParticipantRegistryModel]]] = []
        repeats: list[int] = []
        offset = 0
        for group, size, count in blueprint:
            units.append((group, people[offset : offset + size]))
            repeats.append(count)
            offset += size

        competing, skipped = self._submissions(
            competition=competition,
            categories=categories,
            disciplines=disciplines,
            groups=groups,
            ages=ages,
            formats=formats,
            units=units,
            repeats=repeats,
            acts=acts,
            rng=rng,
        )

        programs: list[tuple[str, str]] = []
        if with_programs:
            service = build_program_service()
            for category in categories:
                view = service.create_program(
                    CreateProgramCommand(
                        competition_id=str(competition.id),
                        name=f"{category.name} — программа",
                        nomination_id=str(category.id),
                        buffer_seconds=30,
                        starts_at=timezone.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=30),
                    )
                )
                programs.append((category.name, view.id))

        self._report(
            competition=competition,
            competing=competing,
            skipped=skipped,
            people=len(people),
            units=len(units),
            programs=programs,
        )

    def _taxonomy(self, competition: CompetitionModel, nominations: int) -> tuple[list[CategoryModel], dict[uuid.UUID, list[DisciplineModel]]]:
        categories: list[CategoryModel] = []
        disciplines: dict[uuid.UUID, list[DisciplineModel]] = {}
        for index, (name, discipline_names) in enumerate(_NOMINATIONS[:nominations]):
            category = CategoryModel.objects.create(competition=competition, name=name, sort_order=index)
            categories.append(category)
            disciplines[category.id] = [
                DisciplineModel.objects.create(competition=competition, category_id=category.id, name=discipline, sort_order=position)
                for position, discipline in enumerate(discipline_names)
            ]
        return categories, disciplines

    def _groups_and_ages(self, competition: CompetitionModel) -> tuple[list[ParticipantGroupModel], dict[uuid.UUID, list[AgeCategoryModel]]]:
        """Составы и их возрастные категории.

        Возрастная категория в этой платформе принадлежит составу, поэтому полос
        столько же на каждый состав — и ``sort_order`` у них проставлен по возрасту,
        а не по алфавиту: это то, что генератор читает вместо названия.
        """
        groups: list[ParticipantGroupModel] = []
        ages: dict[uuid.UUID, list[AgeCategoryModel]] = {}
        for index, (name, minimum, maximum) in enumerate(_GROUPS):
            group = ParticipantGroupModel.objects.create(
                competition=competition,
                name=name,
                min_count=minimum,
                max_count=maximum,
                sort_order=index,
            )
            groups.append(group)
            ages[group.id] = [
                AgeCategoryModel.objects.create(
                    competition=competition,
                    participant_group_id=group.id,
                    name=band,
                    min_age=low,
                    max_age=high,
                    sort_order=position,
                )
                for position, (band, low, high) in enumerate(_AGE_BANDS)
            ]
        return groups, ages

    def _schools(self, owner_id: uuid.UUID, stamp: str) -> list[EducationalOrganizationModel]:
        return [
            EducationalOrganizationModel.objects.create(
                owner_id=owner_id,
                name=f"{name} [демо {stamp}]",
                organization_type="school",
                city=_CITIES[index % len(_CITIES)],
            )
            for index, name in enumerate(_SCHOOLS)
        ]

    def _people(
        self,
        owner_id: uuid.UUID,
        schools: list[EducationalOrganizationModel],
        count: int,
        rng: random.Random,
    ) -> list[ParticipantRegistryModel]:
        """Реестр участников — все с разными подписями.

        Имена идут декартовым произведением пулов, а не по модулю: при 280 людях
        «фамилия[i*7 % 20] имя[i % 16]» даёт восемь десятков подписей на всех, и
        программа, которая знает участника по имени, принимается разводить по залу
        тёзок. Когда произведение кончается, фамилия получает номер.
        """
        today = timezone.now().date()
        people: list[ParticipantRegistryModel] = []
        for index in range(count):
            female = index % 2 == 0
            surnames, forenames = _NAMES_F if female else _NAMES_M
            # Каждый род получает свою половину номеров, поэтому и шагаем по
            # произведению своего пула: соседние индексы одного рода идут подряд.
            slot = index // 2
            combinations = len(surnames) * len(forenames)
            wrap, inside = divmod(slot, combinations)
            surname, forename = divmod(inside, len(forenames))
            people.append(
                ParticipantRegistryModel(
                    owner_id=owner_id,
                    first_name=forenames[forename],
                    last_name=surnames[surname] if wrap == 0 else f"{surnames[surname]}-{wrap + 1}",
                    middle_name=None,
                    birth_date=today.replace(year=today.year - rng.randint(7, 19)) - timedelta(days=rng.randint(0, 364)),
                    gender="female" if female else "male",
                )
            )
        ParticipantRegistryModel.objects.bulk_create(people, batch_size=500)
        ParticipantOrganizationMembershipModel.objects.bulk_create(
            [
                ParticipantOrganizationMembershipModel(
                    participant=person,
                    organization=schools[index % len(schools)],
                    is_primary=True,
                )
                for index, person in enumerate(people)
            ],
            batch_size=500,
        )
        return people

    def _units(
        self,
        groups: list[ParticipantGroupModel],
        acts: int,
        rng: random.Random,
    ) -> list[tuple[ParticipantGroupModel, int, int]]:
        """Исполнители: кто выходит на сцену и сколько номеров привозит.

        Коллектив — это постоянная труппа, а не случайная выборка на каждый номер:
        «Пируэт» везёт три номера одним составом. Это и правда так, и это
        единственный способ получить честные повторы — при выборке наугад из общего
        пула любые два ансамбля по шесть человек пересекаются, развести их нельзя, и
        проверять на таких данных нечего.

        Возвращает ``(состав, размер, сколько номеров)``; людей раздаёт уже
        вызывающий, непересекающимися кусками.
        """
        units: list[tuple[ParticipantGroupModel, int, int]] = []
        planned = 0
        sizes, weights = zip(*_ACTS_PER_UNIT, strict=True)
        while planned < acts:
            group = rng.choice(groups)
            cast = rng.randint(group.min_count, min(group.max_count or group.min_count, 8))
            repeats = rng.choices(sizes, weights=weights, k=1)[0]
            units.append((group, cast, repeats))
            planned += repeats
        return units

    def _submissions(
        self,
        *,
        competition: CompetitionModel,
        categories: list[CategoryModel],
        disciplines: dict[uuid.UUID, list[DisciplineModel]],
        groups: list[ParticipantGroupModel],
        ages: dict[uuid.UUID, list[AgeCategoryModel]],
        formats: list[ParticipationFormatModel],
        units: list[tuple[ParticipantGroupModel, list[ParticipantRegistryModel]]],
        repeats: list[int],
        acts: int,
        rng: random.Random,
    ) -> tuple[int, int]:
        """Заявки: ``acts`` допущенных плюс горсть тех, что в конкурсе не участвуют.

        Номера раздаются исполнителям: один солист — один, два или три номера, и
        всегда в своей возрастной полосе и своём составе. Отсюда берутся повторы,
        которые генератору потом разводить.
        """
        plan: list[tuple[ParticipantGroupModel, list[ParticipantRegistryModel]]] = []
        for (group, cast), count in zip(units, repeats, strict=True):
            plan.extend([(group, cast)] * count)
        rng.shuffle(plan)
        del plan[acts:]

        skipped = max(3, acts // 20)
        rows: list[SubmissionModel] = []
        for index, (group, cast) in enumerate(plan + plan[:skipped]):
            competing = index < acts
            category = categories[index % len(categories)]
            discipline = rng.choice(disciplines[category.id])
            age = rng.choice(ages[group.id])
            rows.append(
                SubmissionModel(
                    competition_id=competition.id,
                    applicant_id=uuid.uuid4(),
                    status=SubmissionStatus.ACCEPTED.value if competing else rng.choice(_NON_COMPETING),
                    performance={
                        "title": f"{rng.choice(_TITLES)} · {index + 1:04d}",
                        # Длительность — то, без чего номер не встаёт в программу вовсе:
                        # каталог молча отбрасывает заявку без неё.
                        "duration_seconds": rng.randint(90, 330),
                        "nomination_id": str(category.id),
                        "discipline_id": str(discipline.id),
                        "participant_group_id": str(group.id),
                        "age_category_id": str(age.id),
                        "participation_format_id": str(rng.choice(formats).id),
                        "comment": rng.choice(_COMMENTS),
                    },
                    participants=[
                        {
                            "id": str(uuid.uuid4()),
                            "display_name": f"{person.last_name} {person.first_name}",
                            "first_name": person.first_name,
                            "last_name": person.last_name,
                            "birth_date": person.birth_date.isoformat(),
                            "member_count": 1,
                            "registry_participant_id": str(person.id),
                        }
                        for person in cast
                    ],
                    teachers=[
                        {"last_name": last, "first_name": first, "middle_name": middle, "role": "Преподаватель"}
                        for last, first, middle in [rng.choice(_TEACHER_NAMES)]
                    ],
                )
            )
        SubmissionModel.objects.bulk_create(rows, batch_size=500)
        return acts, skipped

    # ------------------------------------------------------------------
    # Отчёт, список и уборка
    # ------------------------------------------------------------------

    def _report(
        self,
        *,
        competition: CompetitionModel,
        competing: int,
        skipped: int,
        people: int,
        units: int,
        programs: list[tuple[str, str]],
    ) -> None:
        self.stdout.write(self.style.SUCCESS(f"\nФестиваль «{competition.title}» создан."))
        self.stdout.write(f"  id фестиваля   : {competition.id}")
        self.stdout.write(f"  организация    : {competition.organizer_id}")
        self.stdout.write(f"  допущено       : {competing} выступлений")
        self.stdout.write(f"  не в конкурсе  : {skipped} заявок (их генератор брать не должен)")
        self.stdout.write(f"  участников     : {people} в {units} исполнителях (солисты и постоянные труппы)")
        self.stdout.write(f"  повторных выходов: {competing - units} — их генератору и разводить")
        for name, program_id in programs:
            self.stdout.write(f"  программа      : {name} → {program_id}")
        self.stdout.write("\nОткройте «Программа» в кабинете организатора, выберите этот фестиваль и нажмите «Собрать программу».\n")

    def _list(self) -> None:
        rows = CompetitionModel.objects.filter(**{f"settings__{MARKER}__isnull": False}).order_by("-created_at")
        if not rows:
            self.stdout.write("Засеянных фестивалей нет.")
            return
        for competition in rows:
            entries = SubmissionModel.objects.filter(competition_id=competition.id, deleted_at__isnull=True).count()
            programs = ProgramModel.objects.filter(competition_id=competition.id, deleted_at__isnull=True).count()
            self.stdout.write(f"{competition.id}  {competition.title}  — заявок {entries}, программ {programs}")

    def _cleanup(self) -> None:
        """Убрать всё засеянное — и ничего, кроме.

        Реестр и школы удаляются по владельцу, записанному в настройках самого
        фестиваля: это и есть причина, по которой демо-данные заводятся на
        отдельного владельца, а не на организацию. Чужой реестр так не заденешь.
        """
        festivals = list(CompetitionModel.objects.filter(**{f"settings__{MARKER}__isnull": False}))
        if not festivals:
            self.stdout.write("Удалять нечего.")
            return
        ids = [competition.id for competition in festivals]
        owners = [
            uuid.UUID(str((competition.settings or {}).get(MARKER, {}).get("registryOwnerId")))
            for competition in festivals
            if (competition.settings or {}).get(MARKER, {}).get("registryOwnerId")
        ]
        with transaction.atomic():
            entries = SubmissionModel.objects.filter(competition_id__in=ids).delete()[0]
            programs = ProgramModel.objects.filter(competition_id__in=ids).delete()[0]
            registry = ParticipantRegistryModel.objects.filter(owner_id__in=owners).delete()[0] if owners else 0
            schools = EducationalOrganizationModel.objects.filter(owner_id__in=owners).delete()[0] if owners else 0
            CompetitionModel.objects.filter(id__in=ids).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Удалено: фестивалей {len(ids)}, заявок {entries}, строк программ {programs}, записей реестра {registry}, школ {schools}."
            )
        )
