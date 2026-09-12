import { Download, Plus, QrCode, Trash2, Upload, Vote } from "lucide-react";
import { useRef, useState } from "react";
import { Link } from "react-router";

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
  useBallots,
  useCloseBallot,
  useCreateBallot,
  useDeleteBallot,
  useImportNominees,
  useOpenBallot,
  useRemoveNominee,
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

function NewBallotForm({ onCreated }: { onCreated: (id: string) => void }): React.JSX.Element {
  const create = useCreateBallot();
  const [title, setTitle] = useState("");

  const submit = (event: React.FormEvent): void => {
    event.preventDefault();
    create.mutate(
      { title: title.trim() },
      {
        onSuccess: (ballot) => {
          setTitle("");
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
        <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={submit}>
          <Input
            label="Название"
            required
            className="flex-1"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Приз зрительских симпатий"
          />
          <Button type="submit" loading={create.isPending}>
            <Plus className="size-4" />
            Создать
          </Button>
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
        <CardDescription>
          Ссылка для зала: <span className="break-all font-medium">{link}</span>
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
              variant="ghost"
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
