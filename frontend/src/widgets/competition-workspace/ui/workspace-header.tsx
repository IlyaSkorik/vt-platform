import { CheckCircle2, Flag, Megaphone, PlayCircle } from "lucide-react";
import { useState } from "react";
import type { AutosaveState, PublicationChecklist } from "@/features/competitions";
import { competitionStatusLabel, competitionStatusVariant } from "@/features/competitions";
import type { CompetitionDetail } from "@/shared/api/generated/model-competitions";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui";
import { AutosaveIndicator } from "./autosave-indicator";

interface WorkspaceHeaderProps {
  competition: CompetitionDetail;
  autosaveState: AutosaveState;
  checklist: PublicationChecklist;
  onPublish: () => void;
  onMarkConfigured: () => void;
  onMarkReady: () => void;
  onStart: () => void;
  onComplete: () => void;
  publishing?: boolean;
  markingConfigured?: boolean;
  markingReady?: boolean;
  starting?: boolean;
  completing?: boolean;
}

type ConfirmAction = "publish" | "mark-configured" | "mark-ready" | "start" | "complete" | null;

export function WorkspaceHeader({
  competition,
  autosaveState,
  checklist,
  onPublish,
  onMarkConfigured,
  onMarkReady,
  onStart,
  onComplete,
  publishing = false,
  markingConfigured = false,
  markingReady = false,
  starting = false,
  completing = false,
}: WorkspaceHeaderProps): React.JSX.Element {
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);

  const isCompleted = competition.status === "COMPLETED";
  const canMarkConfigured = competition.status === "DRAFT";
  const canMarkReady = competition.status === "CONFIGURED" && checklist.isPublishable;
  const canPublish = competition.status === "READY";
  const canStart = competition.status === "PUBLISHED";
  const canComplete = competition.status === "RUNNING";

  const confirmCopy: Record<
    Exclude<ConfirmAction, null>,
    { title: string; description: string; confirmLabel: string; onConfirm: () => void }
  > = {
    publish: {
      title: "Опубликовать фестиваль?",
      description:
        "Фестиваль станет виден участникам. Приём заявок открывается и закрывается по каждому жанру в разделе «Регистрация».",
      confirmLabel: "Опубликовать",
      onConfirm: onPublish,
    },
    "mark-configured": {
      title: "Отметить как настроенный?",
      description:
        "Сигнал, что базовая настройка завершена. Редактирование останется доступным; готовность можно отметить после чек-листа.",
      confirmLabel: "Отметить настроенным",
      onConfirm: onMarkConfigured,
    },
    "mark-ready": {
      title: "Отметить как готовый?",
      description:
        "Конфигурация будет зафиксирована для публикации. Сначала закройте оставшиеся пункты чек-листа.",
      confirmLabel: "Отметить готовым",
      onConfirm: onMarkReady,
    },
    start: {
      title: "Начать фестиваль?",
      description:
        "Фестиваль перейдёт в статус «Идёт». Приёмом заявок по-прежнему управляют окна жанров.",
      confirmLabel: "Начать фестиваль",
      onConfirm: onStart,
    },
    complete: {
      title: "Завершить фестиваль?",
      description: "Фестиваль перейдёт в статус «Завершён» и станет доступен только для чтения.",
      confirmLabel: "Завершить фестиваль",
      onConfirm: onComplete,
    },
  };

  const confirmBusy =
    (confirmAction === "publish" && publishing) ||
    (confirmAction === "mark-configured" && markingConfigured) ||
    (confirmAction === "mark-ready" && markingReady) ||
    (confirmAction === "start" && starting) ||
    (confirmAction === "complete" && completing);

  return (
    <header className="sticky top-0 z-[calc(var(--z-sticky) -1 )] border-border border-b bg-background/95 px-4 py-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:px-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate font-bold text-2xl text-foreground tracking-tight">
              {competition.title}
            </h1>
            <Badge variant={competitionStatusVariant(competition.status)}>
              {competitionStatusLabel(competition.status)}
            </Badge>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <AutosaveIndicator state={autosaveState} />
            <span className="inline-flex items-center gap-1.5 text-muted-foreground text-xs">
              <CheckCircle2
                className={
                  checklist.isPublishable ? "size-3.5 text-success" : "size-3.5 text-warning"
                }
                aria-hidden="true"
              />
              {checklist.isPublishable
                ? "Готов к публикации"
                : `Осталось пунктов в чек-листе: ${checklist.blockingIncomplete}`}
            </span>
          </div>
        </div>

        {!isCompleted ? (
          <div className="flex flex-wrap items-center gap-2">
            {canMarkConfigured ? (
              <Button
                variant="outline"
                onClick={() => setConfirmAction("mark-configured")}
                loading={markingConfigured}
              >
                Отметить настроенным
              </Button>
            ) : null}

            {canMarkReady ? (
              <Button
                variant="outline"
                onClick={() => setConfirmAction("mark-ready")}
                loading={markingReady}
              >
                Отметить готовым
              </Button>
            ) : null}

            {canPublish ? (
              <Button onClick={() => setConfirmAction("publish")} loading={publishing}>
                <Megaphone className="size-4" aria-hidden="true" />
                Опубликовать
              </Button>
            ) : null}

            {canStart ? (
              <Button onClick={() => setConfirmAction("start")} loading={starting}>
                <PlayCircle className="size-4" aria-hidden="true" />
                Начать фестиваль
              </Button>
            ) : null}

            {canComplete ? (
              <Button
                variant="outline"
                onClick={() => setConfirmAction("complete")}
                loading={completing}
              >
                <Flag className="size-4" aria-hidden="true" />
                Завершить фестиваль
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>

      <Dialog
        open={confirmAction != null}
        onOpenChange={(open) => {
          if (!open) {
            setConfirmAction(null);
          }
        }}
      >
        <DialogContent>
          {confirmAction ? (
            <>
              <DialogHeader>
                <DialogTitle>{confirmCopy[confirmAction].title}</DialogTitle>
                <DialogDescription>{confirmCopy[confirmAction].description}</DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setConfirmAction(null)}>
                  Отмена
                </Button>
                <Button
                  loading={confirmBusy}
                  onClick={() => {
                    confirmCopy[confirmAction].onConfirm();
                    setConfirmAction(null);
                  }}
                >
                  {confirmCopy[confirmAction].confirmLabel}
                </Button>
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </header>
  );
}
