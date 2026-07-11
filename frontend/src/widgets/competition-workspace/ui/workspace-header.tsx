import { Archive, CheckCircle2, ChevronDown, Megaphone, UserMinus, UserPlus } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
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
  onOpenRegistration: () => void;
  onCloseRegistration: () => void;
  onArchive: () => void;
  publishing?: boolean;
  markingConfigured?: boolean;
  markingReady?: boolean;
  openingRegistration?: boolean;
  closingRegistration?: boolean;
  archiving?: boolean;
}

type ConfirmAction =
  | "publish"
  | "mark-configured"
  | "mark-ready"
  | "open-registration"
  | "close-registration"
  | null;

export function WorkspaceHeader({
  competition,
  autosaveState,
  checklist,
  onPublish,
  onMarkConfigured,
  onMarkReady,
  onOpenRegistration,
  onCloseRegistration,
  onArchive,
  publishing = false,
  markingConfigured = false,
  markingReady = false,
  openingRegistration = false,
  closingRegistration = false,
  archiving = false,
}: WorkspaceHeaderProps): React.JSX.Element {
  const menuId = useId();
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ConfirmAction>(null);

  const isArchived = competition.status === "ARCHIVED";
  const canMarkConfigured = competition.status === "DRAFT";
  const canMarkReady = competition.status === "CONFIGURED" && checklist.isPublishable;
  const canPublish = competition.status === "READY";
  const canOpenRegistration = competition.status === "PUBLISHED";
  const canCloseRegistration = competition.status === "REGISTRATION_OPEN";

  useEffect(() => {
    if (!menuOpen) {
      return;
    }

    const onPointerDown = (event: MouseEvent): void => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };

    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  const confirmCopy: Record<
    Exclude<ConfirmAction, null>,
    { title: string; description: string; confirmLabel: string; onConfirm: () => void }
  > = {
    publish: {
      title: "Опубликовать фестиваль?",
      description:
        "Фестиваль станет доступен согласно настройкам публикации. После этого можно открыть регистрацию.",
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
    "open-registration": {
      title: "Открыть регистрацию?",
      description: "Участники смогут подавать заявки, пока регистрация открыта.",
      confirmLabel: "Открыть регистрацию",
      onConfirm: onOpenRegistration,
    },
    "close-registration": {
      title: "Закрыть регистрацию?",
      description: "Новые заявки больше не будут приниматься.",
      confirmLabel: "Закрыть регистрацию",
      onConfirm: onCloseRegistration,
    },
  };

  const confirmBusy =
    (confirmAction === "publish" && publishing) ||
    (confirmAction === "mark-configured" && markingConfigured) ||
    (confirmAction === "mark-ready" && markingReady) ||
    (confirmAction === "open-registration" && openingRegistration) ||
    (confirmAction === "close-registration" && closingRegistration);

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

        {!isArchived ? (
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

            {canOpenRegistration ? (
              <Button
                variant="outline"
                onClick={() => setConfirmAction("open-registration")}
                loading={openingRegistration}
              >
                <UserPlus className="size-4" aria-hidden="true" />
                Открыть регистрацию
              </Button>
            ) : null}
            {canCloseRegistration ? (
              <Button
                variant="outline"
                onClick={() => setConfirmAction("close-registration")}
                loading={closingRegistration}
              >
                <UserMinus className="size-4" aria-hidden="true" />
                Закрыть регистрацию
              </Button>
            ) : null}

            <div className="relative" ref={menuRef}>
              <Button
                variant="outline"
                onClick={() => setMenuOpen((value) => !value)}
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                aria-controls={menuId}
              >
                Ещё
                <ChevronDown className="size-4" aria-hidden="true" />
              </Button>
              {menuOpen ? (
                <div
                  id={menuId}
                  role="menu"
                  className="absolute top-full right-0 z-[var(--z-dropdown)] mt-2 min-w-44 rounded-md border bg-popover p-1 shadow-elevation-2"
                >
                  <button
                    type="button"
                    role="menuitem"
                    className="flex w-full items-center gap-2 rounded-sm px-3 py-2 text-left text-sm outline-none hover:bg-accent focus-visible:bg-accent focus-visible:ring-2 focus-visible:ring-ring"
                    onClick={() => {
                      setMenuOpen(false);
                      setArchiveOpen(true);
                    }}
                  >
                    <Archive className="size-4" aria-hidden="true" />
                    Архивировать
                  </button>
                </div>
              ) : null}
            </div>
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

      <Dialog open={archiveOpen} onOpenChange={setArchiveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Архивировать фестиваль?</DialogTitle>
            <DialogDescription>
              Архивированный фестиваль станет только для чтения: конфигурацию можно смотреть, но
              редактировать и принимать заявки уже нельзя.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setArchiveOpen(false)}>
              Отмена
            </Button>
            <Button
              variant="danger"
              loading={archiving}
              onClick={() => {
                onArchive();
                setArchiveOpen(false);
              }}
            >
              Архивировать
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </header>
  );
}
