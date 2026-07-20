import {
  CheckCircle2,
  Circle,
  ExternalLink,
  GripVertical,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router";
import {
  type AutosaveState,
  buildContactsSummary,
  type CompetitionSectionId,
  contactsConfigToPayload,
  createTeamContactDraft,
  moveTeamContactBefore,
  type PublicationChecklist,
  resolveContactsConfig,
  sortTeamContacts,
  useOrganizationProfileQuery,
  useUpdateContactsConfigurationMutation,
  useUpdateGeneralInformationMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import type {
  _ContactsConfig,
  _TeamContact,
  CompetitionDetail,
} from "@/shared/api/generated/model-competitions";
import { ROUTES } from "@/shared/config";
import { cn } from "@/shared/lib";
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
  IconButton,
  Input,
  Radio,
  RadioGroup,
  Textarea,
  toast,
} from "@/shared/ui";
import { ContactsSkeleton } from "./contacts-skeleton";

const AUTOSAVE_DELAY_MS = 600;

interface ContactsSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: React.ReactNode;
}): React.JSX.Element {
  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      {children != null ? <CardContent className="space-y-4">{children}</CardContent> : null}
    </Card>
  );
}

function ReadOnlyField({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}): React.JSX.Element {
  return (
    <div className="space-y-1">
      <p className="font-medium text-muted-foreground text-xs uppercase tracking-wide">{label}</p>
      <p className="text-sm">{value?.trim() ? value : "Не указано"}</p>
    </div>
  );
}

function ContactsSummaryPanel({
  summary,
}: {
  summary: ReturnType<typeof buildContactsSummary>;
}): React.JSX.Element {
  const items = [
    { id: "org", label: "Профиль организации", done: summary.organizationProfile },
    { id: "people", label: "Контакты фестиваля", done: summary.competitionContacts },
    { id: "venue", label: "Площадка", done: summary.venue },
    { id: "emergency", label: "Экстренная связь", done: summary.emergency },
  ] as const;
  const doneCount = items.filter((item) => item.done).length;
  const percent = Math.round((doneCount / items.length) * 100);

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Сводка контактов</CardTitle>
        <CardDescription>
          {percent}% ·{" "}
          {doneCount === items.length ? "Раздел заполнен" : `Осталось: ${items.length - doneCount}`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-[width]"
            style={{ width: `${percent}%` }}
          />
        </div>
        <ul className="space-y-1" aria-label="Сводка контактов">
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-2 px-2 py-1.5 text-sm">
              {item.done ? (
                <CheckCircle2 className="size-4 shrink-0 text-success" aria-hidden="true" />
              ) : (
                <Circle className="size-4 shrink-0 text-warning" aria-hidden="true" />
              )}
              <span className="min-w-0 flex-1 truncate">{item.label}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

interface TeamContactFormValues {
  name: string;
  position: string;
  phone: string;
  email: string;
  description: string;
}

function TeamContactDialog({
  open,
  mode,
  initial,
  onOpenChange,
  onSubmit,
}: {
  open: boolean;
  mode: "create" | "edit";
  initial: TeamContactFormValues;
  onOpenChange: (open: boolean) => void;
  onSubmit: (values: TeamContactFormValues) => void;
}): React.JSX.Element {
  const [values, setValues] = useState(initial);
  useEffect(() => {
    if (open) setValues(initial);
  }, [open, initial]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Новый контакт" : "Редактировать контакт"}</DialogTitle>
          <DialogDescription>Контакт относится только к этому фестивалю.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <Input
            label="Имя"
            required
            value={values.name}
            onChange={(event) => setValues((prev) => ({ ...prev, name: event.target.value }))}
          />
          <Input
            label="Должность"
            value={values.position}
            onChange={(event) => setValues((prev) => ({ ...prev, position: event.target.value }))}
            placeholder="Координатор, пресса…"
          />
          <Input
            label="Телефон"
            value={values.phone}
            onChange={(event) => setValues((prev) => ({ ...prev, phone: event.target.value }))}
          />
          <Input
            label="Email"
            type="email"
            value={values.email}
            onChange={(event) => setValues((prev) => ({ ...prev, email: event.target.value }))}
          />
          <Textarea
            label="Описание"
            value={values.description}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, description: event.target.value }))
            }
          />
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Отмена
          </Button>
          <Button type="button" disabled={!values.name.trim()} onClick={() => onSubmit(values)}>
            Сохранить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ContactsSection({
  competition,
  isLoading = false,
  onAutosaveStateChange,
}: ContactsSectionProps): React.JSX.Element {
  const isReadOnly = competition.status === "ARCHIVED";
  const orgQuery = useOrganizationProfileQuery();
  const updateConfig = useUpdateContactsConfigurationMutation();
  const updateGeneral = useUpdateGeneralInformationMutation();

  const effectiveConfig = useMemo(() => resolveContactsConfig(competition), [competition]);
  const [config, setConfig] = useState<_ContactsConfig>(effectiveConfig);
  const [venueName, setVenueName] = useState(competition.venue?.name ?? "");
  const [venueAddress, setVenueAddress] = useState(competition.venue?.address ?? "");

  // Mirror the committed config so `updateConfigLocal` can compute the next value
  // (and schedule the save) outside the `setConfig` updater — the updater must be
  // pure, and scheduling a save touches parent state (autosave status).
  const configRef = useRef(config);
  useEffect(() => {
    configRef.current = config;
  }, [config]);

  useEffect(() => {
    setConfig(effectiveConfig);
  }, [effectiveConfig]);

  useEffect(() => {
    setVenueName(competition.venue?.name ?? "");
    setVenueAddress(competition.venue?.address ?? "");
  }, [competition.venue?.name, competition.venue?.address]);

  const autosaveTimer = useRef<number | null>(null);
  const venueTimer = useRef<number | null>(null);
  const saveGeneration = useRef(0);

  const persistConfig = useCallback(
    async (next: _ContactsConfig) => {
      saveGeneration.current += 1;
      const gen = saveGeneration.current;
      onAutosaveStateChange("saving");
      try {
        await updateConfig.mutateAsync({
          competitionId: competition.id,
          payload: contactsConfigToPayload(next),
        });
        if (gen === saveGeneration.current) onAutosaveStateChange("saved");
      } catch (error) {
        if (gen === saveGeneration.current) {
          onAutosaveStateChange("error");
          const message =
            error instanceof ApiError
              ? (error.problem?.detail ?? "Не удалось сохранить контакты")
              : "Не удалось сохранить контакты";
          toast.error(message);
        }
      }
    },
    [competition.id, updateConfig, onAutosaveStateChange],
  );

  const scheduleConfigSave = useCallback(
    (next: _ContactsConfig) => {
      if (autosaveTimer.current != null) window.clearTimeout(autosaveTimer.current);
      onAutosaveStateChange("dirty");
      autosaveTimer.current = window.setTimeout(() => {
        void persistConfig(next);
      }, AUTOSAVE_DELAY_MS);
    },
    [persistConfig, onAutosaveStateChange],
  );

  const updateConfigLocal = useCallback(
    (patch: Partial<_ContactsConfig> | ((prev: _ContactsConfig) => _ContactsConfig)) => {
      if (isReadOnly) return;
      const prev = configRef.current;
      const next = typeof patch === "function" ? patch(prev) : { ...prev, ...patch };
      // Keep the ref current so back-to-back calls in the same tick see the
      // latest value before the effect re-syncs it after commit.
      configRef.current = next;
      setConfig(next);
      scheduleConfigSave(next);
    },
    [isReadOnly, scheduleConfigSave],
  );

  const persistVenue = useCallback(
    async (name: string, address: string) => {
      onAutosaveStateChange("saving");
      try {
        await updateGeneral.mutateAsync({
          competitionId: competition.id,
          payload: {
            title: competition.title,
            season: competition.season,
            description: competition.description,
            logo: competition.branding.logo,
            banner: competition.branding.banner,
            venueName: name.trim() || null,
            venueAddress: address.trim() || null,
            registrationStart: competition.registrationPeriod?.start ?? null,
            registrationEnd: competition.registrationPeriod?.end ?? null,
            competitionStart: competition.competitionPeriod?.start ?? null,
            competitionEnd: competition.competitionPeriod?.end ?? null,
          },
        });
        onAutosaveStateChange("saved");
      } catch (error) {
        onAutosaveStateChange("error");
        const message =
          error instanceof ApiError
            ? (error.problem?.detail ?? "Не удалось сохранить площадку")
            : "Не удалось сохранить площадку";
        toast.error(message);
      }
    },
    [competition, updateGeneral, onAutosaveStateChange],
  );

  const scheduleVenueSave = useCallback(
    (name: string, address: string) => {
      if (venueTimer.current != null) window.clearTimeout(venueTimer.current);
      onAutosaveStateChange("dirty");
      venueTimer.current = window.setTimeout(() => {
        void persistVenue(name, address);
      }, AUTOSAVE_DELAY_MS);
    },
    [persistVenue, onAutosaveStateChange],
  );

  useEffect(
    () => () => {
      if (autosaveTimer.current != null) window.clearTimeout(autosaveTimer.current);
      if (venueTimer.current != null) window.clearTimeout(venueTimer.current);
    },
    [],
  );

  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<"create" | "edit">("create");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [dialogInitial, setDialogInitial] = useState<TeamContactFormValues>({
    name: "",
    position: "",
    phone: "",
    email: "",
    description: "",
  });
  const [deleteTarget, setDeleteTarget] = useState<_TeamContact | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);

  const teamContacts = useMemo(() => sortTeamContacts(config.teamContacts), [config.teamContacts]);
  const summary = useMemo(
    () => buildContactsSummary(competition, config, orgQuery.data?.name),
    [competition, config, orgQuery.data?.name],
  );

  const openCreate = (): void => {
    setDialogMode("create");
    setEditingId(null);
    setDialogInitial({ name: "", position: "", phone: "", email: "", description: "" });
    setDialogOpen(true);
  };

  const openEdit = (contact: _TeamContact): void => {
    setDialogMode("edit");
    setEditingId(contact.id);
    setDialogInitial({
      name: contact.name,
      position: contact.position ?? "",
      phone: contact.phone ?? "",
      email: contact.email ?? "",
      description: contact.description ?? "",
    });
    setDialogOpen(true);
  };

  const handleDialogSubmit = (values: TeamContactFormValues): void => {
    updateConfigLocal((prev) => {
      if (dialogMode === "create") {
        const draft = {
          ...createTeamContactDraft(prev.teamContacts.length),
          name: values.name.trim(),
          position: values.position.trim() || null,
          phone: values.phone.trim() || null,
          email: values.email.trim() || null,
          description: values.description.trim() || null,
        };
        return { ...prev, teamContacts: [...prev.teamContacts, draft] };
      }
      return {
        ...prev,
        teamContacts: prev.teamContacts.map((item) =>
          item.id === editingId
            ? {
                ...item,
                name: values.name.trim(),
                position: values.position.trim() || null,
                phone: values.phone.trim() || null,
                email: values.email.trim() || null,
                description: values.description.trim() || null,
              }
            : item,
        ),
      };
    });
    setDialogOpen(false);
  };

  if (isLoading) return <ContactsSkeleton />;

  const org = orgQuery.data;
  const sourceValue = config.useOrganizationContacts ? "organization" : "custom";

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="min-w-0 space-y-4">
        <div>
          <h2 className="font-semibold text-lg">Контакты</h2>
          <p className="text-muted-foreground text-sm">
            По умолчанию используются контакты организации. Дублируйте данные только при
            необходимости.
          </p>
        </div>

        {isReadOnly ? (
          <Alert variant="warning" title="Фестиваль в архиве">
            Контакты доступны только для просмотра.
          </Alert>
        ) : null}

        <SectionCard
          title="Источник контактов"
          description="Организация — единый источник правды. Переопределение только для этого фестиваля."
        >
          <RadioGroup
            value={sourceValue}
            disabled={isReadOnly}
            onValueChange={(value) =>
              updateConfigLocal({ useOrganizationContacts: value !== "custom" })
            }
          >
            <Radio
              value="organization"
              label="Использовать контакты организации"
              description={org?.name ?? "Загрузка профиля организации…"}
            />
            <Radio
              value="custom"
              label="Настроить контакты для этого фестиваля"
              description="Переопределить поля организации только здесь"
            />
          </RadioGroup>

          {config.useOrganizationContacts ? (
            <div className="space-y-4 rounded-lg border border-border bg-muted/30 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-sm">Организация</p>
                  <p className="text-muted-foreground text-sm">{org?.name ?? "—"}</p>
                </div>
                <Button asChild type="button" variant="outline" size="sm">
                  <Link to={ROUTES.staffOrganization}>
                    Открыть профиль организации
                    <ExternalLink className="size-3.5" aria-hidden="true" />
                  </Link>
                </Button>
              </div>
              {orgQuery.isError ? (
                <Alert variant="danger" title="Не удалось загрузить профиль">
                  {orgQuery.error instanceof ApiError
                    ? (orgQuery.error.problem?.detail ?? "Повторите позже")
                    : "Повторите позже"}
                </Alert>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  <ReadOnlyField label="Название" value={org?.name} />
                  <ReadOnlyField label="Логотип" value={org?.logo} />
                  <ReadOnlyField label="Телефон" value={org?.phone} />
                  <ReadOnlyField label="Email" value={org?.email} />
                  <ReadOnlyField label="Сайт" value={org?.website} />
                  <ReadOnlyField label="Адрес" value={org?.address} />
                  <ReadOnlyField label="VK" value={org?.vk} />
                  <ReadOnlyField label="Instagram" value={org?.instagram} />
                  <ReadOnlyField label="Telegram" value={org?.telegram} />
                  <ReadOnlyField label="Юридическая информация" value={org?.legalInformation} />
                </div>
              )}
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {(
                [
                  ["organizationName", "Название организации"],
                  ["phone", "Телефон"],
                  ["email", "Email"],
                  ["website", "Сайт"],
                  ["address", "Адрес"],
                  ["vk", "VK"],
                  ["instagram", "Instagram"],
                  ["telegram", "Telegram"],
                ] as const
              ).map(([key, label]) => (
                <Input
                  key={key}
                  label={label}
                  disabled={isReadOnly}
                  value={config.override[key] ?? ""}
                  onChange={(event) =>
                    updateConfigLocal({
                      override: { ...config.override, [key]: event.target.value },
                    })
                  }
                />
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="Контакты фестиваля"
          description="Люди и роли именно этого фестиваля — координатор, пресса, проживание и др."
        >
          {teamContacts.length === 0 ? (
            <EmptyState
              title="Пока нет контактов"
              description="Добавьте координатора, техподдержку или другие роли."
              action={
                isReadOnly ? undefined : (
                  <Button type="button" onClick={openCreate}>
                    <Plus className="size-4" aria-hidden="true" />
                    Добавить контакт
                  </Button>
                )
              }
            />
          ) : (
            <ul className="space-y-2">
              {teamContacts.map((contact) => (
                <li
                  key={contact.id}
                  draggable={!isReadOnly}
                  onDragStart={() => setDraggedId(contact.id)}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={() => {
                    if (!draggedId) return;
                    updateConfigLocal((prev) => ({
                      ...prev,
                      teamContacts: moveTeamContactBefore(prev.teamContacts, draggedId, contact.id),
                    }));
                    setDraggedId(null);
                  }}
                  className={cn(
                    "flex items-start gap-2 rounded-lg border border-border bg-card px-3 py-3",
                    draggedId === contact.id && "opacity-60",
                  )}
                >
                  <GripVertical
                    className="mt-1 size-4 shrink-0 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-sm">{contact.name}</p>
                    {contact.position ? (
                      <p className="text-muted-foreground text-xs">{contact.position}</p>
                    ) : null}
                    <p className="mt-1 text-muted-foreground text-xs">
                      {[contact.phone, contact.email].filter(Boolean).join(" · ") || "Без связи"}
                    </p>
                    {contact.description ? (
                      <p className="mt-1 text-sm">{contact.description}</p>
                    ) : null}
                  </div>
                  {!isReadOnly ? (
                    <div className="flex shrink-0 gap-1">
                      <IconButton
                        type="button"
                        aria-label="Редактировать"
                        variant="ghost"
                        icon={<Pencil className="size-4" />}
                        onClick={() => openEdit(contact)}
                      />
                      <IconButton
                        type="button"
                        aria-label="Удалить"
                        variant="ghost"
                        icon={<Trash2 className="size-4" />}
                        onClick={() => setDeleteTarget(contact)}
                      />
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          {!isReadOnly && teamContacts.length > 0 ? (
            <Button type="button" variant="outline" onClick={openCreate}>
              <Plus className="size-4" aria-hidden="true" />
              Добавить контакт
            </Button>
          ) : null}
        </SectionCard>

        <SectionCard title="Площадка" description="Где проходит фестиваль и как добраться.">
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Название площадки"
              disabled={isReadOnly}
              value={venueName}
              onChange={(event) => {
                const next = event.target.value;
                setVenueName(next);
                scheduleVenueSave(next, venueAddress);
              }}
            />
            <Input
              label="Адрес"
              disabled={isReadOnly}
              value={venueAddress}
              onChange={(event) => {
                const next = event.target.value;
                setVenueAddress(next);
                scheduleVenueSave(venueName, next);
              }}
            />
            <Input
              label="Город"
              disabled={isReadOnly}
              value={config.venueDetails.city ?? ""}
              onChange={(event) =>
                updateConfigLocal({
                  venueDetails: { ...config.venueDetails, city: event.target.value },
                })
              }
            />
            <Input
              label="Страна"
              disabled={isReadOnly}
              value={config.venueDetails.country ?? ""}
              onChange={(event) =>
                updateConfigLocal({
                  venueDetails: { ...config.venueDetails, country: event.target.value },
                })
              }
            />
            <Input
              label="Google Maps"
              disabled={isReadOnly}
              value={config.venueDetails.googleMapsUrl ?? ""}
              onChange={(event) =>
                updateConfigLocal({
                  venueDetails: { ...config.venueDetails, googleMapsUrl: event.target.value },
                })
              }
            />
            <Input
              label="Яндекс Карты"
              disabled={isReadOnly}
              value={config.venueDetails.yandexMapsUrl ?? ""}
              onChange={(event) =>
                updateConfigLocal({
                  venueDetails: { ...config.venueDetails, yandexMapsUrl: event.target.value },
                })
              }
            />
          </div>
          <Textarea
            label="Как добраться"
            disabled={isReadOnly}
            value={config.venueDetails.directions ?? ""}
            onChange={(event) =>
              updateConfigLocal({
                venueDetails: { ...config.venueDetails, directions: event.target.value },
              })
            }
          />
        </SectionCard>

        <SectionCard
          title="Экстренная связь"
          description="Необязательно. Для участников и родителей."
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              label="Экстренный телефон"
              disabled={isReadOnly}
              value={config.emergency.phone ?? ""}
              onChange={(event) =>
                updateConfigLocal({
                  emergency: { ...config.emergency, phone: event.target.value },
                })
              }
            />
            <Input
              label="Экстренный email"
              type="email"
              disabled={isReadOnly}
              value={config.emergency.email ?? ""}
              onChange={(event) =>
                updateConfigLocal({
                  emergency: { ...config.emergency, email: event.target.value },
                })
              }
            />
          </div>
          <Textarea
            label="Заметки"
            disabled={isReadOnly}
            value={config.emergency.notes ?? ""}
            onChange={(event) =>
              updateConfigLocal({
                emergency: { ...config.emergency, notes: event.target.value },
              })
            }
          />
        </SectionCard>
      </div>

      <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
        <ContactsSummaryPanel summary={summary} />
      </aside>

      <TeamContactDialog
        open={dialogOpen}
        mode={dialogMode}
        initial={dialogInitial}
        onOpenChange={setDialogOpen}
        onSubmit={handleDialogSubmit}
      />

      <Dialog open={deleteTarget != null} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Удалить контакт?</DialogTitle>
            <DialogDescription>
              «{deleteTarget?.name}» будет удалён из контактов фестиваля.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setDeleteTarget(null)}>
              Отмена
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={() => {
                if (!deleteTarget) return;
                updateConfigLocal((prev) => ({
                  ...prev,
                  teamContacts: prev.teamContacts.filter((item) => item.id !== deleteTarget.id),
                }));
                setDeleteTarget(null);
              }}
            >
              Удалить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
