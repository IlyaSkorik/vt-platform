import { AlertTriangle, Search, Trash2 } from "lucide-react";
import { useState } from "react";

import {
  PURGE_MIN_QUERY,
  type PurgeKind,
  type PurgeTarget,
  refusalMessage,
  usePurge,
  usePurgePlan,
  usePurgeSearch,
} from "@/applications/platform/api/platform-api";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  Input,
  LoadingState,
  Select,
  toast,
} from "@/shared/ui";

/**
 * What the operator can point the eraser at, in the order the console offers it.
 *
 * Ordered by how often a support request actually names one, not by how much data
 * each takes with it: a cancelled festival and a "удалите мои данные" letter are
 * the two that arrive, and the rest are the long tail behind them.
 */
const KINDS: { value: PurgeKind; label: string; hint: string; placeholder: string }[] = [
  {
    value: "festival",
    label: "Фестиваль",
    hint: "Заявки, выступления, дипломы, программы и протоколы этого фестиваля. Организация, её сотрудники и шаблоны дипломов остаются.",
    placeholder: "Название фестиваля или его id",
  },
  {
    value: "account",
    label: "Аккаунт",
    hint: "Аккаунт и всё, что заведено под ним: заявки, реестр участников и педагогов, уведомления, сессии и согласия. Фестивали организаций, где человек в штате, остаются.",
    placeholder: "E-mail, фамилия или id",
  },
  {
    value: "application",
    label: "Заявка",
    hint: "Одна заявка с её выступлениями и дипломами. Фестиваль, его номинации и программа остаются — из них уходят только номера этой заявки.",
    placeholder: "E-mail заявителя или id заявки",
  },
  {
    value: "organization",
    label: "Организация",
    hint: "Организация, все её фестивали целиком, роли сотрудников и шаблоны дипломов. Аккаунты сотрудников остаются.",
    placeholder: "Название, адрес или id",
  },
  {
    value: "participant",
    label: "Участник реестра",
    hint: "Карточка участника из реестра заявителя. В уже поданных заявках имя останется — это снимок того, что было заявлено.",
    placeholder: "Фамилия, название коллектива или id",
  },
  {
    value: "teacher",
    label: "Педагог реестра",
    hint: "Карточка педагога из реестра заявителя. В уже поданных заявках педагог останется указан.",
    placeholder: "Фамилия или id",
  },
];

const FALLBACK_KIND = KINDS[0] as (typeof KINDS)[number];

function kindOf(value: PurgeKind): (typeof KINDS)[number] {
  return KINDS.find((kind) => kind.value === value) ?? FALLBACK_KIND;
}

/**
 * The confirmation, and the only place the deletion can be started from.
 *
 * The plan is loaded and shown *before* the button exists, because "удалить
 * фестиваль" and "удалить фестиваль вместе с 340 дипломами" are different
 * decisions and only one of them is being made here. Retyping the name is what
 * turns a click into a decision: the id is already in the URL, so a guard that
 * only checked the id would guard nothing.
 */
function ConfirmDialog({
  target,
  onClose,
}: {
  target: PurgeTarget;
  onClose: () => void;
}): React.JSX.Element {
  const plan = usePurgePlan(target.kind, target.id);
  const erase = usePurge();
  const [typed, setTyped] = useState("");

  const normalise = (value: string): string =>
    value.trim().replace(/\s+/g, " ").toLocaleLowerCase();
  const matches = normalise(typed) === normalise(target.label);

  const submit = (event: React.FormEvent): void => {
    event.preventDefault();
    erase.mutate(
      { kind: target.kind, id: target.id, confirm: typed },
      {
        onSuccess: (removed) => {
          toast.success(
            `Удалено: «${removed.target.label}» — ${removed.total} записей и ${removed.files} файлов.`,
          );
          onClose();
        },
        onError: async (error) => {
          toast.error(await refusalMessage(error, "Не удалось удалить"));
        },
      },
    );
  };

  return (
    <Dialog open onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Удалить безвозвратно</DialogTitle>
          <DialogDescription>
            {kindOf(target.kind).label}: <span className="font-medium">{target.label}</span> —{" "}
            {target.hint}
          </DialogDescription>
        </DialogHeader>

        {plan.isLoading ? <LoadingState label="Считаем, что будет удалено" /> : null}
        {plan.isError ? (
          <Alert variant="danger" title="Не удалось посчитать">
            Проверьте, что объект ещё существует, и откройте диалог заново.
          </Alert>
        ) : null}

        {plan.data ? (
          <>
            {plan.data.warnings.map((warning) => (
              <Alert key={warning} variant="warning">
                {warning}
              </Alert>
            ))}

            <div className="scrollbar-custom max-h-56 overflow-y-auto rounded-lg border border-border">
              <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 p-3 text-sm">
                {plan.data.rows.map((row) => (
                  <div key={row.table} className="col-span-2 grid grid-cols-subgrid">
                    <dt className="text-muted-foreground" title={row.table}>
                      {row.label}
                    </dt>
                    <dd className="text-right font-medium tabular-nums">{row.count}</dd>
                  </div>
                ))}
              </dl>
            </div>

            <p className="text-sm">
              Всего <span className="font-medium tabular-nums">{plan.data.total}</span> записей и{" "}
              <span className="font-medium tabular-nums">{plan.data.files}</span> файлов. Отмены не
              будет — это не скрытие, а физическое удаление из базы и хранилища.
            </p>

            <form className="flex flex-col gap-3" onSubmit={submit}>
              <Input
                label="Введите название, чтобы подтвердить"
                autoComplete="off"
                value={typed}
                onChange={(event) => setTyped(event.target.value)}
                description={`Ожидается: ${target.label}`}
              />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={onClose}>
                  Отмена
                </Button>
                <Button
                  type="submit"
                  variant="danger"
                  disabled={!matches}
                  loading={erase.isPending}
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                  Удалить безвозвратно
                </Button>
              </DialogFooter>
            </form>
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

/**
 * The operator's eraser.
 *
 * Deliberately a search and not a listing. Everything else in this console is a
 * view over the whole platform, which is what a console is for; this one screen is
 * not, because a browsable table next to an irreversible button builds exactly the
 * habit that ends in the wrong row being deleted. The operator arrives here with a
 * specific festival or a specific person, and has to name it.
 */
export function PlatformErasePage(): React.JSX.Element {
  const [kind, setKind] = useState<PurgeKind>("festival");
  const [query, setQuery] = useState("");
  const [target, setTarget] = useState<PurgeTarget | null>(null);

  const selected = kindOf(kind);
  const results = usePurgeSearch(kind, query);
  const searching = query.trim().length >= PURGE_MIN_QUERY;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="font-semibold text-2xl">Удаление данных</h1>
        <p className="text-muted-foreground text-sm">
          Полное удаление объекта вместе со всем, что к нему привязано.
        </p>
      </header>

      <Alert variant="danger" title="Это не «скрыть», а «удалить»">
        Везде на платформе удаление мягкое — запись остаётся в базе и её можно вернуть. Здесь нет:
        строки удаляются из базы физически, а файлы (дипломы, фонограммы, чеки, документы) — из
        хранилища. Восстановить их можно будет только из резервной копии. Перед удалением консоль
        покажет, что именно уйдёт.
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Что удаляем</CardTitle>
          <CardDescription>{selected.hint}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <Select
              label="Тип объекта"
              value={kind}
              onValueChange={(next) => {
                setKind(next as PurgeKind);
                // The old results describe a different kind of thing entirely, and
                // leaving them under a new heading is how the wrong row gets clicked.
                setQuery("");
              }}
              options={KINDS.map((item) => ({ value: item.value, label: item.label }))}
            />
            <Input
              label="Поиск"
              autoComplete="off"
              placeholder={selected.placeholder}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              leadingIcon={<Search className="size-4" aria-hidden="true" />}
              description={`Минимум ${PURGE_MIN_QUERY} символа — список целиком консоль не показывает`}
            />
          </div>
        </CardContent>
      </Card>

      {results.isLoading && searching ? <LoadingState label="Ищем" /> : null}

      {results.isError ? (
        <EmptyState
          title="Не удалось выполнить поиск"
          description="Проверьте доступ к консоли платформы и повторите попытку."
        />
      ) : null}

      {searching && results.data?.length === 0 ? (
        <EmptyState
          title="Ничего не найдено"
          description="Уточните запрос или вставьте идентификатор объекта целиком."
        />
      ) : null}

      {results.data && results.data.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {results.data.map((candidate) => (
            <li
              key={candidate.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border p-4"
            >
              <span className="flex min-w-0 flex-col">
                <span className="truncate font-medium">{candidate.label}</span>
                <span className="truncate text-muted-foreground text-sm">{candidate.hint}</span>
                <span className="truncate font-mono text-muted-foreground text-xs">
                  {candidate.id}
                </span>
              </span>
              <Button
                variant="outline"
                className="text-danger"
                onClick={() => setTarget(candidate)}
              >
                <AlertTriangle className="size-4" aria-hidden="true" />
                Удалить…
              </Button>
            </li>
          ))}
        </ul>
      ) : null}

      {target ? <ConfirmDialog target={target} onClose={() => setTarget(null)} /> : null}
    </div>
  );
}
