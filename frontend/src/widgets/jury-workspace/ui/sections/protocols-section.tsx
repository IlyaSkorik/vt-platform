import { CheckCircle2, CircleDashed, Plus } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { useCompetitionDetail, useCompetitionsList } from "@/features/competitions";
import {
  type ProtocolSummary,
  useCreateProtocol,
  useProtocol,
  useProtocols,
} from "@/features/jury-protocols";
import { ApiError } from "@/shared/api";
import { cn } from "@/shared/lib";
import {
  Badge,
  Button,
  EmptyState,
  LoadingState,
  Select,
  type SelectOption,
  toast,
} from "@/shared/ui";

import { ProtocolEditor } from "../protocol-editor";

/** One nomination of the chosen competition, with its protocol if it has one. */
interface NominationRow {
  id: string;
  name: string;
  protocol: ProtocolSummary | undefined;
}

/**
 * Протоколы — the jury's results, one nomination at a time.
 *
 * The shape of the screen follows the shape of the work: a festival is judged nomination by
 * nomination, so the left column is **every nomination of the competition** rather than every
 * protocol that happens to exist. A nomination with no protocol yet is listed too, with the
 * button that opens one — otherwise the first question a jury asks ("где вокал?") would be
 * answered by an empty list.
 *
 * The competition is the section's context and is asked once, up front, the same way the
 * diplomas workspace asks for it: an organizer works on one festival at a time, and putting
 * that question inside every subsequent action made a form out of a glance.
 */
export function ProtocolsSection(): React.JSX.Element {
  const [competitionId, setCompetitionId] = useState("");
  const [selectedNominationId, setSelectedNominationId] = useState<string | null>(null);

  const competitionsQuery = useCompetitionsList();
  const competitionDetailQuery = useCompetitionDetail(competitionId || undefined);
  const protocolsQuery = useProtocols(competitionId || undefined);
  const createProtocol = useCreateProtocol();

  const competitionOptions: SelectOption[] = useMemo(
    () => (competitionsQuery.data ?? []).map((item) => ({ value: item.id, label: item.title })),
    [competitionsQuery.data],
  );

  const nominations: NominationRow[] = useMemo(() => {
    const byNomination = new Map(
      (protocolsQuery.data ?? []).map((protocol) => [protocol.nominationId, protocol]),
    );
    return (competitionDetailQuery.data?.categories ?? []).map((category) => ({
      id: category.id,
      name: category.name,
      protocol: byNomination.get(category.id),
    }));
  }, [competitionDetailQuery.data, protocolsQuery.data]);

  const selected = nominations.find((nomination) => nomination.id === selectedNominationId);
  const protocolQuery = useProtocol(selected?.protocol?.id ?? null);

  const handleCompetitionChange = useCallback((value: string): void => {
    setCompetitionId(value);
    // The old nomination belongs to the old festival; keeping it selected would show one
    // competition's protocol under another's name.
    setSelectedNominationId(null);
  }, []);

  const handleCreate = useCallback(
    async (nomination: NominationRow): Promise<void> => {
      try {
        const protocol = await createProtocol.mutateAsync({
          competitionId,
          nominationId: nomination.id,
        });
        setSelectedNominationId(nomination.id);
        toast.success(
          protocol.seededFromProgramId != null
            ? `Протокол создан по программе: строк ${protocol.rows.length}`
            : `Протокол создан: строк ${protocol.rows.length}`,
        );
      } catch (error) {
        const message =
          error instanceof ApiError
            ? (error.problem?.detail ?? "Не удалось создать протокол.")
            : "Не удалось создать протокол.";
        toast.error(message);
      }
    },
    [competitionId, createProtocol],
  );

  return (
    <div className="flex flex-col gap-4">
      <Select
        label="Фестиваль"
        placeholder="Выберите фестиваль"
        options={competitionOptions}
        value={competitionId}
        onValueChange={handleCompetitionChange}
        containerClassName="max-w-md"
      />

      {competitionId === "" ? (
        <EmptyState
          title="Выберите фестиваль"
          description="Протоколы ведутся по номинациям выбранного фестиваля."
        />
      ) : competitionDetailQuery.isLoading || protocolsQuery.isLoading ? (
        <LoadingState label="Загружаем номинации…" />
      ) : nominations.length === 0 ? (
        <EmptyState
          title="У фестиваля нет номинаций"
          description="Добавьте номинации в разделе «Номинации и дисциплины» фестиваля — протокол ведётся по номинации."
        />
      ) : (
        <div className="flex min-h-0 min-w-0 flex-col gap-4 lg:flex-row">
          <nav aria-label="Номинации" className="w-full shrink-0 lg:w-72">
            <ul className="flex flex-col gap-1">
              {nominations.map((nomination) => {
                const isActive = nomination.id === selectedNominationId;
                const protocol = nomination.protocol;
                return (
                  <li key={nomination.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedNominationId(nomination.id)}
                      aria-current={isActive ? "true" : undefined}
                      className={cn(
                        "flex w-full flex-col gap-1 rounded-md border border-transparent px-3 py-2 text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring",
                        isActive
                          ? "border-border bg-accent text-accent-foreground"
                          : "hover:bg-accent/60",
                      )}
                    >
                      <span className="flex items-center gap-2">
                        <span className="min-w-0 flex-1 truncate font-medium text-sm">
                          {nomination.name}
                        </span>
                        {protocol == null ? null : protocol.status === "PUBLISHED" ? (
                          <Badge variant={protocol.hasUnpublishedChanges ? "warning" : "success"}>
                            {protocol.hasUnpublishedChanges ? "Изменён" : "Опубликован"}
                          </Badge>
                        ) : (
                          <Badge variant="neutral">Черновик</Badge>
                        )}
                      </span>
                      {protocol == null ? (
                        <span className="text-muted-foreground text-xs">Протокола ещё нет</span>
                      ) : (
                        <span className="flex items-center gap-1 text-muted-foreground text-xs">
                          {protocol.decidedCount === protocol.rowCount ? (
                            <CheckCircle2 className="size-3.5" aria-hidden="true" />
                          ) : (
                            <CircleDashed className="size-3.5" aria-hidden="true" />
                          )}
                          Результатов: {protocol.decidedCount} из {protocol.rowCount}
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>

          <div className="min-w-0 flex-1">
            {selected == null ? (
              <EmptyState
                title="Выберите номинацию"
                description="Слева — номинации фестиваля. Для каждой ведётся свой протокол."
              />
            ) : selected.protocol == null ? (
              <EmptyState
                title={`Протокола по номинации «${selected.name}» ещё нет`}
                description="Протокол откроется в порядке выступления: строки и номера подтянутся из программы этой номинации, а если программы нет — из допущенных заявок."
                action={
                  <Button
                    onClick={() => void handleCreate(selected)}
                    loading={createProtocol.isPending}
                  >
                    <Plus className="size-4" aria-hidden="true" />
                    Создать протокол
                  </Button>
                }
              />
            ) : protocolQuery.isLoading ? (
              <LoadingState label="Загружаем протокол…" />
            ) : protocolQuery.data == null ? (
              <EmptyState
                title="Не удалось загрузить протокол"
                description="Обновите страницу или выберите номинацию заново."
              />
            ) : (
              <ProtocolEditor protocol={protocolQuery.data} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
