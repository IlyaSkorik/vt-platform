import { CheckCircle2, ChevronDown, Circle, FileText, Music, Receipt, Video } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AUDIO_FORMAT_OPTIONS,
  type AutosaveState,
  buildCompetitionReadiness,
  type CompetitionSectionId,
  defaultCompetitionSettings,
  MEDIA_FORMAT_OPTIONS,
  MEDIA_MODE_OPTIONS,
  mergeSettingsWithFormats,
  type PublicationChecklist,
  settingsToUpdatePayload,
  useUpdateCompetitionSettingsMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import type {
  _FormatRequirements,
  _Settings,
  CompetitionDetail,
} from "@/shared/api/generated/model-competitions";
import { cn } from "@/shared/lib";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Checkbox,
  EmptyState,
  Input,
  Select,
  Switch,
  toast,
} from "@/shared/ui";
import { SettingsSkeleton } from "./settings-skeleton";

const AUTOSAVE_DELAY_MS = 500;

interface SettingsSectionProps {
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

/**
 * One setting row.
 *
 * Every row rendered here is a setting the platform actually acts on — the ones it
 * merely stored were removed rather than shown as pending (see
 * ``UNENFORCED_SETTINGS``), so there is no "disabled but visible" state to model.
 */
function SwitchRow({
  label,
  description,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (val: boolean) => void;
}): React.JSX.Element {
  return (
    <Switch
      label={label}
      description={description}
      checked={checked}
      disabled={disabled}
      onCheckedChange={onChange}
      containerClassName="flex-row-reverse justify-between"
    />
  );
}

function CheckboxGroup<T extends string>({
  options,
  value,
  disabled,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T[];
  disabled?: boolean;
  onChange: (next: T[]) => void;
}): React.JSX.Element {
  const toggle = (item: T, checked: boolean): void => {
    if (checked) onChange([...value, item]);
    else onChange(value.filter((entry) => entry !== item));
  };

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {options.map((opt) => (
        <Checkbox
          key={opt.value}
          label={opt.label}
          checked={value.includes(opt.value)}
          disabled={disabled}
          onCheckedChange={(next) => toggle(opt.value, Boolean(next))}
        />
      ))}
    </div>
  );
}

function MaterialBlock({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <div className="space-y-3 border-border border-t pt-4 first:border-t-0 first:pt-0">
      <p className="flex items-center gap-1.5 font-semibold text-muted-foreground text-xs uppercase tracking-wide">
        {icon}
        {title}
      </p>
      {children}
    </div>
  );
}

function FormatRequirementsAccordion({
  formatName,
  requirements,
  readOnly,
  onChange,
}: {
  formatName: string;
  requirements: _FormatRequirements;
  readOnly: boolean;
  onChange: (updated: _FormatRequirements) => void;
}): React.JSX.Element {
  const update = (patch: Partial<_FormatRequirements>): void =>
    onChange({ ...requirements, ...patch });

  return (
    <details className="group rounded-lg border border-border bg-card open:shadow-sm">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 font-medium text-sm [&::-webkit-details-marker]:hidden">
        <ChevronDown
          className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180"
          aria-hidden="true"
        />
        <span className="min-w-0 flex-1 truncate">{formatName}</span>
        <Badge variant="secondary" size="sm">
          Музыка · Медиа · Квитанция
        </Badge>
      </summary>
      <div className="space-y-1 border-border border-t px-4 py-4">
        <MaterialBlock icon={<Music className="size-3.5" />} title="Музыка">
          <SwitchRow
            label="Требовать загрузку"
            description="Без трека заявку подать нельзя."
            checked={requirements.music.requireUpload}
            disabled={readOnly}
            onChange={(v) => update({ music: { ...requirements.music, requireUpload: v } })}
          />
          {/* "Разрешить замену" is not rendered: `allow_replacement` is stored and echoed back
              but never read outside the competitions module, so the switch promised a rule
              nothing enforces. Hidden rather than badged, for the same reason as the others. */}
          <div>
            <p className="mb-1.5 font-medium text-sm">Допустимые аудиоформаты</p>
            <p className="mb-1.5 text-muted-foreground text-xs">
              Загрузка файла другого расширения будет отклонена.
            </p>
            <CheckboxGroup
              options={AUDIO_FORMAT_OPTIONS}
              value={requirements.music.allowedFormats as string[]}
              disabled={readOnly}
              onChange={(v) => update({ music: { ...requirements.music, allowedFormats: v } })}
            />
          </div>
          <Input
            label="Максимальный размер (МБ)"
            type="number"
            min={1}
            max={512}
            value={String(requirements.music.maxUploadSizeMb)}
            disabled={readOnly}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (!Number.isFinite(next)) return;
              update({
                music: {
                  ...requirements.music,
                  maxUploadSizeMb: Math.min(512, Math.max(1, Math.round(next))),
                },
              });
            }}
          />
        </MaterialBlock>

        <MaterialBlock icon={<Video className="size-3.5" />} title="Медиа">
          <div>
            <p className="mb-1.5 font-medium text-sm">Режим</p>
            <Select
              options={MEDIA_MODE_OPTIONS}
              value={requirements.media.mode}
              onValueChange={(v) =>
                update({
                  media: {
                    ...requirements.media,
                    mode: (v as _FormatRequirements["media"]["mode"]) ?? "NOT_REQUIRED",
                  },
                })
              }
              disabled={readOnly}
              placeholder="Выберите режим…"
            />
          </div>
          {/* The upload rules appear only once a file is actually collected: settings for
              an upload that never happens are noise, and the fields would invite the
              organizer to tune a limit nothing enforces. Video is not only a remote-entry
              matter — an in-person festival takes the file to play on the hall's screen. */}
          {requirements.media.mode === "FILE_ONLY" || requirements.media.mode === "URL_OR_FILE" ? (
            <>
              <SwitchRow
                label="Требовать медиа"
                description="Выключено — файлы можно приложить, но заявку примут и без них."
                checked={requirements.media.requireUpload}
                disabled={readOnly}
                onChange={(v) => update({ media: { ...requirements.media, requireUpload: v } })}
              />
              <div>
                <p className="mb-1.5 font-medium text-sm">Допустимые форматы видео и фото</p>
                <p className="mb-1.5 text-muted-foreground text-xs">
                  Загрузка файла другого расширения будет отклонена.
                </p>
                <CheckboxGroup
                  options={MEDIA_FORMAT_OPTIONS}
                  value={requirements.media.allowedFormats as string[]}
                  disabled={readOnly}
                  onChange={(v) => update({ media: { ...requirements.media, allowedFormats: v } })}
                />
              </div>
              <Input
                label="Суммарный размер всех файлов (МБ)"
                type="number"
                min={1}
                max={512}
                description="Лимит на все медиафайлы номера вместе. Участник увидит его до загрузки, а сервер откажет, когда сумма не помещается."
                value={String(requirements.media.maxTotalSizeMb)}
                disabled={readOnly}
                onChange={(event) => {
                  const next = Number(event.target.value);
                  if (!Number.isFinite(next)) return;
                  update({
                    media: {
                      ...requirements.media,
                      maxTotalSizeMb: Math.min(512, Math.max(1, Math.round(next))),
                    },
                  });
                }}
              />
            </>
          ) : null}
        </MaterialBlock>

        <MaterialBlock icon={<Receipt className="size-3.5" />} title="Квитанция">
          <SwitchRow
            label="Требовать квитанцию"
            description="Без подтверждения оплаты заявку нельзя отметить оплаченной."
            checked={requirements.paymentReceipt.requireReceipt}
            disabled={readOnly}
            onChange={(v) =>
              update({ paymentReceipt: { ...requirements.paymentReceipt, requireReceipt: v } })
            }
          />
          {requirements.paymentReceipt.requireReceipt ? (
            <SwitchRow
              label="Разрешить загрузить позже"
              description="Выключите, чтобы квитанция требовалась уже при подаче заявки."
              checked={requirements.paymentReceipt.allowUploadLater}
              disabled={readOnly}
              onChange={(v) =>
                update({
                  paymentReceipt: { ...requirements.paymentReceipt, allowUploadLater: v },
                })
              }
            />
          ) : null}
        </MaterialBlock>
      </div>
    </details>
  );
}

function CompetitionReadinessPanel({
  competition,
  checklist,
  onNavigateSection,
}: {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}): React.JSX.Element {
  const readiness = useMemo(
    () => buildCompetitionReadiness(competition, checklist),
    [competition, checklist],
  );

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Готовность фестиваля</CardTitle>
        <CardDescription>
          {readiness.percent}% ·{" "}
          {readiness.incomplete === 0
            ? "Все разделы на месте"
            : `Осталось разделов: ${readiness.incomplete}`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-[width]"
            style={{ width: `${readiness.percent}%` }}
          />
        </div>
        <ul className="space-y-1" aria-label="Готовность конфигурации">
          {readiness.items.map((item) => (
            <li key={item.sectionId}>
              <Button
                type="button"
                variant="ghost"
                className="h-auto w-full justify-start gap-2 px-2 py-1.5 text-left font-normal"
                onClick={() => onNavigateSection(item.sectionId)}
              >
                {item.done ? (
                  <CheckCircle2 className="size-4 shrink-0 text-success" aria-hidden="true" />
                ) : (
                  <Circle
                    className={cn(
                      "size-4 shrink-0",
                      item.blocking ? "text-warning" : "text-muted-foreground",
                    )}
                    aria-hidden="true"
                  />
                )}
                <span className="min-w-0 flex-1 truncate text-sm">{item.label}</span>
              </Button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export function SettingsSection({
  competition,
  checklist,
  isLoading = false,
  onAutosaveStateChange,
  onNavigateSection,
}: SettingsSectionProps): React.JSX.Element {
  const isReadOnly = competition.status === "COMPLETED";
  const updateSettings = useUpdateCompetitionSettingsMutation();

  const effectiveSettings = useMemo(
    () =>
      mergeSettingsWithFormats(
        competition.settings ?? defaultCompetitionSettings(),
        competition.participationFormats ?? [],
      ),
    [competition],
  );

  const [settings, setSettings] = useState<_Settings>(effectiveSettings);

  useEffect(() => {
    setSettings(effectiveSettings);
  }, [effectiveSettings]);

  const autosaveTimer = useRef<number | null>(null);
  const saveGeneration = useRef(0);

  const persist = useCallback(
    async (next: _Settings) => {
      saveGeneration.current += 1;
      const gen = saveGeneration.current;
      onAutosaveStateChange("saving");
      try {
        await updateSettings.mutateAsync({
          competitionId: competition.id,
          payload: settingsToUpdatePayload(next),
        });
        if (gen === saveGeneration.current) {
          onAutosaveStateChange("saved");
        }
      } catch (error) {
        if (gen === saveGeneration.current) {
          onAutosaveStateChange("error");
          const message =
            error instanceof ApiError
              ? (error.problem?.detail ?? "Не удалось сохранить правила участия")
              : "Не удалось сохранить правила участия";
          toast.error(message);
        }
      }
    },
    [competition.id, updateSettings, onAutosaveStateChange],
  );

  const scheduleSave = useCallback(
    (next: _Settings) => {
      if (autosaveTimer.current != null) {
        window.clearTimeout(autosaveTimer.current);
      }
      onAutosaveStateChange("dirty");
      autosaveTimer.current = window.setTimeout(() => {
        void persist(next);
      }, AUTOSAVE_DELAY_MS);
    },
    [persist, onAutosaveStateChange],
  );

  const update = useCallback(
    (patch: Partial<_Settings>) => {
      if (isReadOnly) return;
      setSettings((prev) => {
        const next = { ...prev, ...patch };
        scheduleSave(next);
        return next;
      });
    },
    [isReadOnly, scheduleSave],
  );

  const updateFormatRequirements = useCallback(
    (updated: _FormatRequirements) => {
      if (isReadOnly) return;
      setSettings((prev) => {
        const next: _Settings = {
          ...prev,
          formatRequirements: prev.formatRequirements.map((item) =>
            item.participationFormatId === updated.participationFormatId ? updated : item,
          ),
        };
        scheduleSave(next);
        return next;
      });
    },
    [isReadOnly, scheduleSave],
  );

  useEffect(
    () => () => {
      if (autosaveTimer.current != null) {
        window.clearTimeout(autosaveTimer.current);
      }
    },
    [],
  );

  if (isLoading) {
    return <SettingsSkeleton />;
  }

  const formats = competition.participationFormats ?? [];

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="min-w-0 space-y-4">
        <div>
          <h2 className="font-semibold text-lg">Правила участия</h2>
          <p className="text-muted-foreground text-sm">
            Что участник обязан приложить и подтвердить, чтобы подать заявку.
          </p>
        </div>

        {isReadOnly ? (
          <Alert variant="warning" title="Фестиваль в архиве">
            Правила участия доступны только для просмотра.
          </Alert>
        ) : null}

        <SectionCard title="Подача заявки" description="Как участник создаёт и меняет заявку.">
          <SwitchRow
            label="Педагог обязателен"
            description="Заявку нельзя подать, не указав педагога."
            checked={settings.requireTeacher}
            disabled={isReadOnly}
            onChange={(v) => update({ requireTeacher: v })}
          />
          <SwitchRow
            label="Комментарий участника"
            description="Свободное примечание к выступлению для организаторов."
            checked={settings.participantCommentEnabled}
            disabled={isReadOnly}
            onChange={(v) => update({ participantCommentEnabled: v })}
          />
          <SwitchRow
            label="Данные родителя / опекуна обязательны"
            description="У каждого участника должен быть подтверждённый опекун в реестре."
            checked={settings.requireParentGuardian}
            disabled={isReadOnly}
            onChange={(v) => update({ requireParentGuardian: v })}
          />
        </SectionCard>

        <SectionCard
          title="Материалы заявки"
          description="Требования к музыке, медиа и квитанции — отдельно для каждого формата участия."
        >
          {formats.length === 0 ? (
            <EmptyState
              title="Нет форматов участия"
              description="Сначала добавьте форматы — для каждого появятся свои требования."
              action={
                <Button type="button" onClick={() => onNavigateSection("participation-formats")}>
                  К форматам участия
                </Button>
              }
            />
          ) : (
            <div className="space-y-2">
              {settings.formatRequirements.map((req) => {
                const format = formats.find((item) => item.id === req.participationFormatId);
                return (
                  <FormatRequirementsAccordion
                    key={req.participationFormatId}
                    formatName={format?.name ?? req.participationFormatId}
                    requirements={req}
                    readOnly={isReadOnly}
                    onChange={updateFormatRequirements}
                  />
                );
              })}
            </div>
          )}

          <div className="space-y-3 border-border border-t pt-4">
            <p className="flex items-center gap-1.5 font-semibold text-muted-foreground text-xs uppercase tracking-wide">
              <FileText className="size-3.5" />
              Документы
            </p>
            <p className="text-muted-foreground text-xs">
              Общие правила документов для всех форматов. Типы документов настраиваются отдельно.
            </p>
            <SwitchRow
              label="Требовать загрузку документов"
              description="Без документа заявку подать нельзя."
              checked={settings.requireDocumentUpload}
              disabled={isReadOnly}
              onChange={(v) => update({ requireDocumentUpload: v })}
            />
          </div>
        </SectionCard>

        <SectionCard title="Согласия" description="Что участник подтверждает при подаче заявки.">
          <SwitchRow
            label="Согласие на обработку персональных данных"
            checked={settings.requirePersonalDataConsent}
            disabled={isReadOnly}
            onChange={(v) => update({ requirePersonalDataConsent: v })}
          />
          <SwitchRow
            label="Согласие на фото / медиа"
            checked={settings.requireMediaConsent}
            disabled={isReadOnly}
            onChange={(v) => update({ requireMediaConsent: v })}
          />
          <SwitchRow
            label="Принятие положения фестиваля"
            checked={settings.requireRegulationsAcceptance}
            disabled={isReadOnly}
            onChange={(v) => update({ requireRegulationsAcceptance: v })}
          />
        </SectionCard>
      </div>

      <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
        <CompetitionReadinessPanel
          competition={competition}
          checklist={checklist}
          onNavigateSection={onNavigateSection}
        />
      </aside>
    </div>
  );
}
