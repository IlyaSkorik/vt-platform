import { Copy, Download, ListPlus, Plus, QrCode, Trash2, Upload, Vote } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router";
import { useAuth } from "@/app/providers";
import { useCompetitionsList } from "@/features/competitions";
import {
  ANTI_FRAUD_NOTE,
  type Ballot,
  ballotDownloadUrl,
  type ImportPreview,
  openBlockedReason,
  publicUrl,
  REVEAL_OPTIONS,
  type RevealPolicy,
  revealWarning,
  STATUS_LABELS,
  statusVariant,
  useAddNominee,
  useBallot,
  useBallotPrograms,
  useBallots,
  useCloseBallot,
  useCreateBallot,
  useDeleteBallot,
  useImportNominees,
  useOpenBallot,
  useRemoveNominee,
  useSeedFromProgram,
  useUpdateBallot,
  votable,
} from "@/features/voting-builder";
import { apiClient } from "@/shared/api";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  LoadingState,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageTitle,
  Select,
  toast,
} from "@/shared/ui";

/**
 * Put the voting link on the clipboard.
 *
 * This address goes onto a poster, into a chat and onto a slide, and retyping a
 * ten-character slug by eye is exactly how a hall ends up at a 404. Refusal is
 * possible (an insecure origin, a denied permission), and showing the URL is a
 * worse experience than copying it and a better one than silence.
 */
async function copyLink(link: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(link);
    toast.success("Ссылка скопирована");
  } catch {
    toast.error(`Не удалось скопировать. Ссылка: ${link}`);
  }
}

/** Fetch a staff file through the API client, so the auth header travels with it. */
async function download(path: string, filename: string): Promise<void> {
  const blob = await apiClient(path).blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

/** What the festival picker shows when a ballot belongs to nothing in particular. */
const STANDALONE = "standalone";

function NewBallotForm({ onCreated }: { onCreated: (id: string) => void }): React.JSX.Element {
  const create = useCreateBallot();
  // A voting-only organization was never sold the festivals module, and asking for
  // its festivals would answer 403. Then there is nothing to attach a ballot to,
  // which is the ordinary case here rather than a degraded one.
  const { hasModule } = useAuth();
  const festivals = useCompetitionsList({ enabled: hasModule("COMPETITIONS") });
  const [title, setTitle] = useState("");
  const [competitionId, setCompetitionId] = useState(STANDALONE);

  const options = [
    { value: STANDALONE, label: "Без фестиваля" },
    ...(festivals.data ?? []).map((festival) => ({
      value: festival.id,
      label: `${festival.title} · ${festival.season}`,
    })),
  ];

  const submit = (event: React.FormEvent): void => {
    event.preventDefault();
    create.mutate(
      {
        title: title.trim(),
        ...(competitionId === STANDALONE ? {} : { competitionId }),
      },
      {
        onSuccess: (ballot) => {
          setTitle("");
          setCompetitionId(STANDALONE);
          onCreated(ballot.id);
          toast.success("Голосование создано");
        },
        onError: (error) => toast.error(error.message || "Не удалось создать голосование"),
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Новое голосование</CardTitle>
        <CardDescription>
          Фестиваль на платформе для этого не нужен: список участников можно ввести вручную или
          загрузить из Excel.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-3" onSubmit={submit}>
          <Input
            label="Название"
            required
            // Full width rather than sharing a row with the button: these names run
            // to "Приз зрительских симпатий фестиваля «Весна-2026»", and a field
            // showing a third of that is a field people fight with.
            className="w-full"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Приз зрительских симпатий"
          />
          {options.length > 1 ? (
            <Select
              label="Фестиваль"
              options={options}
              value={competitionId}
              onValueChange={setCompetitionId}
              description="Привязанное к фестивалю голосование можно заполнить из готовой программы"
            />
          ) : null}
          <div>
            <Button type="submit" loading={create.isPending}>
              <Plus className="size-4" />
              Создать
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function ImportBlock({ ballotId }: { ballotId: string }): React.JSX.Element {
  const importNominees = useImportNominees(ballotId);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const choose = (chosen: File): void => {
    setFile(chosen);
    // Always a preview first. An import that silently pours 150 rows of somebody
    // else's formatting into a ballot is one that gets undone by hand.
    importNominees.mutate(
      { file: chosen, dryRun: true },
      {
        onSuccess: setPreview,
        onError: (error) => {
          setPreview(null);
          setFile(null);
          toast.error(error.message || "Не удалось прочитать файл");
        },
      },
    );
  };

  const confirm = (): void => {
    if (!file) return;
    importNominees.mutate(
      { file, dryRun: false },
      {
        onSuccess: (result) => {
          toast.success(`Добавлено участников: ${result.added.length}`);
          setPreview(null);
          setFile(null);
          if (input.current) input.current.value = "";
        },
        onError: (error) => toast.error(error.message || "Не удалось добавить участников"),
      },
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            void download(ballotDownloadUrl(ballotId, "template"), "Номинанты — шаблон.xlsx")
          }
        >
          <Download className="size-4" />
          Скачать шаблон
        </Button>
        <Button
          variant="outline"
          size="sm"
          loading={importNominees.isPending}
          onClick={() => input.current?.click()}
        >
          <Upload className="size-4" />
          Загрузить список
        </Button>
        <input
          ref={input}
          data-testid="import-input"
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={(event) => {
            const chosen = event.target.files?.[0];
            if (chosen) choose(chosen);
          }}
        />
      </div>

      {preview ? (
        <div className="flex flex-col gap-3 rounded-md border border-border p-3">
          <p className="font-medium text-sm">
            Будет добавлено участников: {preview.added.length}
            {preview.errors.length > 0 ? `, строк с ошибками: ${preview.errors.length}` : ""}
          </p>

          {preview.errors.length > 0 ? (
            <ul className="flex flex-col gap-1 text-sm text-warning">
              {preview.errors.map((error) => (
                <li key={error.row}>
                  Строка {error.row}: {error.message}
                </li>
              ))}
            </ul>
          ) : null}

          {preview.missingColumns.length > 0 ? (
            <p className="text-muted-foreground text-xs">
              Колонки не найдены и пропущены: {preview.missingColumns.join(", ")}
            </p>
          ) : null}

          <div className="flex gap-2">
            <Button size="sm" loading={importNominees.isPending} onClick={confirm}>
              Добавить
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setPreview(null);
                setFile(null);
              }}
            >
              Отмена
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Filling the list from a running order — the festival half of this feature.
 *
 * Only rendered for a ballot that named a festival. A standalone one is typed in
 * or imported from a spreadsheet, and offering it a disabled programme picker
 * would advertise a capability it does not have.
 *
 * Each option carries its act count, so the choice between «День 1» and «День 2»
 * is made on what is in them rather than on a name.
 */
function SeedFromProgramBlock({ ballotId }: { ballotId: string }): React.JSX.Element | null {
  const programs = useBallotPrograms(ballotId);
  const seed = useSeedFromProgram(ballotId);
  const [programId, setProgramId] = useState<string | null>(null);

  const options = programs.data ?? [];
  const chosen = programId ?? options[0]?.id ?? null;

  if (programs.isLoading) {
    return <LoadingState label="Загружаем программы" size="sm" />;
  }

  if (options.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border p-3">
      <p className="font-medium text-sm">Заполнить из программы фестиваля</p>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <Select
          label="Программа"
          className="flex-1"
          options={options.map((program) => ({
            value: program.id,
            label: `${program.name} · номеров: ${program.nominees}`,
          }))}
          value={chosen ?? ""}
          onValueChange={setProgramId}
        />
        <Button
          variant="outline"
          loading={seed.isPending}
          disabled={!chosen}
          onClick={() => {
            if (!chosen) return;
            seed.mutate(chosen, {
              onSuccess: (ballot) =>
                toast.success(`Участников в голосовании: ${votable(ballot).length}`),
              onError: (error) => toast.error(error.message || "Не удалось заполнить список"),
            });
          }}
        >
          <ListPlus className="size-4" />
          Подтянуть участников
        </Button>
      </div>
      <p className="text-muted-foreground text-xs">
        Номера копируются в голосование как его собственные участники: программу потом можно менять
        или удалить, список останется.
      </p>
    </div>
  );
}

function NomineeList({ ballot }: { ballot: Ballot }): React.JSX.Element {
  const add = useAddNominee(ballot.id);
  const remove = useRemoveNominee(ballot.id);
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");

  const submit = (event: React.FormEvent): void => {
    event.preventDefault();
    add.mutate(
      { title: title.trim(), subtitle: subtitle.trim() },
      {
        onSuccess: () => {
          setTitle("");
          setSubtitle("");
        },
        onError: (error) => toast.error(error.message || "Не удалось добавить участника"),
      },
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <form className="flex flex-col gap-2 sm:flex-row sm:items-end" onSubmit={submit}>
        <Input
          label="Участник"
          required
          className="flex-1"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Ансамбль «Ритм»"
        />
        <Input
          label="Произведение"
          className="flex-1"
          value={subtitle}
          onChange={(event) => setSubtitle(event.target.value)}
          placeholder="«Калинка»"
        />
        <Button type="submit" variant="outline" loading={add.isPending}>
          Добавить
        </Button>
      </form>

      {ballot.nominees.length === 0 ? (
        <EmptyState
          icon={<Vote aria-hidden="true" />}
          title="Участников пока нет"
          description="Добавьте их по одному или загрузите список из Excel."
        />
      ) : (
        <ul className="flex flex-col divide-y divide-border">
          {ballot.nominees.map((nominee) => (
            <li key={nominee.id} className="flex items-center justify-between gap-3 py-2">
              <span className="min-w-0">
                <span className="block truncate text-sm">
                  {nominee.number !== null ? `${nominee.number}. ` : ""}
                  {nominee.title}
                  {nominee.withdrawn ? " — снят" : ""}
                </span>
                {nominee.subtitle ? (
                  <span className="block truncate text-muted-foreground text-xs">
                    {nominee.subtitle}
                  </span>
                ) : null}
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <Badge variant="neutral">{nominee.votes}</Badge>
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`Убрать «${nominee.title}»`}
                  onClick={() =>
                    remove.mutate(nominee.id, {
                      onError: (error) => toast.error(error.message || "Не удалось убрать"),
                    })
                  }
                >
                  <Trash2 className="size-4" />
                </Button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function BallotEditor({ ballotId }: { ballotId: string }): React.JSX.Element {
  const { data: ballot, isLoading } = useBallot(ballotId);
  const update = useUpdateBallot(ballotId);
  const open = useOpenBallot(ballotId);
  const close = useCloseBallot(ballotId);

  if (isLoading || !ballot) {
    return <LoadingState label="Загружаем голосование" />;
  }

  const blocked = openBlockedReason(ballot);
  const warning = revealWarning(ballot.reveal);
  const link = publicUrl(ballot.slug);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>{ballot.title}</CardTitle>
          <Badge variant={statusVariant(ballot.status)}>{STATUS_LABELS[ballot.status]}</Badge>
        </div>
        <CardDescription className="flex flex-wrap items-center gap-2">
          <span>Ссылка для зала:</span>
          <span className="break-all font-medium">{link}</span>
          <Button
            variant="ghost"
            size="sm"
            aria-label="Скопировать ссылку"
            onClick={() => void copyLink(link)}
          >
            <Copy className="size-4" />
            Скопировать
          </Button>
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="flex flex-wrap gap-2">
          {ballot.status === "OPEN" ? (
            <Button
              variant="outline"
              loading={close.isPending}
              onClick={() =>
                close.mutate(undefined, {
                  onSuccess: () => toast.success("Голосование завершено"),
                  onError: (error) => toast.error(error.message || "Не удалось завершить"),
                })
              }
            >
              Завершить
            </Button>
          ) : (
            <Button
              loading={open.isPending}
              disabled={Boolean(blocked)}
              onClick={() =>
                open.mutate(undefined, {
                  onSuccess: () => toast.success("Голосование открыто"),
                  onError: (error) => toast.error(error.message || "Не удалось открыть"),
                })
              }
            >
              Открыть голосование
            </Button>
          )}
          <Button variant="outline" asChild>
            <Link to={`/vote/${ballot.slug}/board`} target="_blank" rel="noreferrer">
              Открыть табло
            </Link>
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              void download(ballotDownloadUrl(ballot.id, "qr"), `qr-${ballot.slug}.png`)
            }
          >
            <QrCode className="size-4" />
            QR для афиши
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              void download(ballotDownloadUrl(ballot.id, "results"), `${ballot.title} — итоги.xlsx`)
            }
          >
            <Download className="size-4" />
            Выгрузить итоги
          </Button>
        </div>

        {blocked ? <Alert variant="warning">{blocked}</Alert> : null}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Input
            label="Голосов на человека"
            type="number"
            min={1}
            max={10}
            className="sm:max-w-48"
            defaultValue={ballot.votesPerVoter}
            onBlur={(event) => {
              const value = Number(event.target.value);
              if (value !== ballot.votesPerVoter && value >= 1) {
                update.mutate({ votesPerVoter: value });
              }
            }}
          />
          <Select
            label="Показ результатов"
            className="sm:max-w-64"
            options={REVEAL_OPTIONS}
            value={ballot.reveal}
            onValueChange={(value) => update.mutate({ reveal: value as RevealPolicy })}
          />
        </div>

        {warning ? <Alert variant="warning">{warning}</Alert> : null}
        {/* The honest version rather than the flattering one — see ANTI_FRAUD_NOTE. */}
        <p className="text-muted-foreground text-xs">{ANTI_FRAUD_NOTE}</p>

        <div className="flex flex-col gap-2">
          <p className="font-medium text-sm">
            Участники ({votable(ballot).length}) · проголосовало: {ballot.voters}
          </p>
          <SeedFromProgramBlock ballotId={ballot.id} />
          <ImportBlock ballotId={ballot.id} />
          <NomineeList ballot={ballot} />
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * `/staff/voting` — the organizer's audience votes.
 *
 * A section of its own rather than a tab inside a festival, because a ballot does
 * not need a festival: an organizer who came to this platform only for the
 * audience vote works entirely from here.
 */
export function StaffVotingPage(): React.JSX.Element {
  const ballots = useBallots();
  const remove = useDeleteBallot();
  const [selected, setSelected] = useState<string | null>(null);

  const rows = ballots.data ?? [];
  const current = selected ?? rows[0]?.id ?? null;

  return (
    <PageContainer size="wide">
      <PageHeader>
        <PageTitle>Зрительское голосование</PageTitle>
        <PageDescription>
          Голосование зала — с фестивалем на платформе или само по себе.
        </PageDescription>
      </PageHeader>
      <PageContent className="flex flex-col gap-6">
        <NewBallotForm onCreated={setSelected} />

        {ballots.isLoading ? <LoadingState label="Загружаем голосования" /> : null}

        {!ballots.isLoading && rows.length === 0 ? (
          <EmptyState
            icon={<Vote aria-hidden="true" />}
            title="Голосований пока нет"
            description="Создайте первое — участников можно добавить вручную или из файла."
          />
        ) : null}

        <div className="grid gap-4 lg:grid-cols-[20rem_1fr]">
          {rows.length > 0 ? (
            <ul className="flex flex-col gap-2">
              {rows.map((row) => (
                <li key={row.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(row.id)}
                    className={`flex w-full flex-col gap-1 rounded-md border p-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      row.id === current
                        ? "border-primary bg-primary/5"
                        : "border-border hover:bg-accent"
                    }`}
                  >
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate font-medium text-sm">{row.title}</span>
                      <Badge variant={statusVariant(row.status)}>{STATUS_LABELS[row.status]}</Badge>
                    </span>
                    <span className="text-muted-foreground text-xs">
                      участников: {row.nominees} · голосов: {row.totalVotes}
                      {row.standalone ? " · без фестиваля" : ""}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}

          {current ? <BallotEditor key={current} ballotId={current} /> : null}
        </div>

        {current ? (
          <div>
            <Button
              // Red, because it is not undoable: the ballot stops resolving for the
              // hall, and a button that looks like every other one is one people
              // press on the way past.
              variant="danger"
              loading={remove.isPending}
              onClick={() =>
                remove.mutate(current, {
                  onSuccess: () => {
                    setSelected(null);
                    toast.success("Голосование удалено");
                  },
                  onError: (error) => toast.error(error.message || "Не удалось удалить"),
                })
              }
            >
              <Trash2 className="size-4" />
              Удалить это голосование
            </Button>
          </div>
        ) : null}
      </PageContent>
    </PageContainer>
  );
}
