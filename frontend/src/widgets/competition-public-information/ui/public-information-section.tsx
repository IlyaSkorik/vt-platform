import { CheckCircle2, ChevronDown, Circle, GripVertical, Plus, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  type AutosaveState,
  blockDisplayTitle,
  buildLandingStructure,
  type CompetitionSectionId,
  createContentBlock,
  createFaqItem,
  createGalleryImage,
  createJuryCard,
  createPartnerCard,
  isSystemBlock,
  landingConfigToPayload,
  moveLandingBlockBefore,
  type PublicationChecklist,
  resolveContactsConfig,
  resolveLandingConfig,
  sortLandingBlocks,
  useUpdateLandingConfigurationMutation,
  useUploadLandingImageMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import type {
  _LandingBlock,
  _LandingConfig,
  CompetitionDetail,
} from "@/shared/api/generated/model-competitions";
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
  Switch,
  Textarea,
  toast,
} from "@/shared/ui";
import { LandingImageUploadField } from "./landing-image-upload-field";
import { LandingPreview } from "./landing-preview";
import { PublicInformationSkeleton } from "./public-information-skeleton";

const AUTOSAVE_DELAY_MS = 600;

interface PublicInformationSectionProps {
  competition: CompetitionDetail;
  checklist: PublicationChecklist;
  isLoading?: boolean;
  onAutosaveStateChange: (state: AutosaveState) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
}

function LandingStructurePanel({ config }: { config: _LandingConfig }): React.JSX.Element {
  const items = buildLandingStructure(config);
  const enabledCount = items.filter((item) => item.enabled).length;
  const percent = items.length === 0 ? 0 : Math.round((enabledCount / items.length) * 100);

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Структура лендинга</CardTitle>
        <CardDescription>
          {percent}% · {enabledCount} из {items.length} блоков показано
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-[width]"
            style={{ width: `${percent}%` }}
          />
        </div>
        <ul className="space-y-1" aria-label="Структура лендинга">
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-2 px-2 py-1.5 text-sm">
              {item.enabled ? (
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

function BlockEditor({
  block,
  competition,
  isReadOnly,
  uploading,
  onChange,
  onNavigateSection,
  onUploadImage,
}: {
  block: _LandingBlock;
  competition: CompetitionDetail;
  isReadOnly: boolean;
  uploading: boolean;
  onChange: (next: _LandingBlock) => void;
  onNavigateSection: (sectionId: CompetitionSectionId) => void;
  onUploadImage: (file: File) => Promise<string>;
}): React.JSX.Element {
  const galleryInputRef = useRef<HTMLInputElement>(null);
  const cards = block.cards ?? [];
  const partners = block.partners ?? [];
  const images = block.images ?? [];
  const faqItems = block.faqItems ?? [];

  switch (block.type) {
    case "HERO":
      return (
        <div className="space-y-3">
          <Input
            label="Заголовок"
            disabled={isReadOnly}
            value={block.title ?? ""}
            onChange={(event) => onChange({ ...block, title: event.target.value })}
          />
          <Input
            label="Подзаголовок"
            disabled={isReadOnly}
            value={block.subtitle ?? ""}
            onChange={(event) => onChange({ ...block, subtitle: event.target.value })}
          />
          <LandingImageUploadField
            label="Обложка"
            value={block.coverImage}
            disabled={isReadOnly}
            uploading={uploading}
            aspectClassName="aspect-[16/9]"
            widthClassName="max-w-xl"
            hint="Так обложка кадрируется в шапке страницы фестиваля (на телефоне она показывается целиком)."
            onUpload={async (file) => {
              const fileReference = await onUploadImage(file);
              onChange({ ...block, coverImage: fileReference });
            }}
            onClear={() => onChange({ ...block, coverImage: null })}
          />
        </div>
      );
    case "VENUE": {
      const contacts = resolveContactsConfig(competition);
      const details = contacts.venueDetails;
      return (
        <div className="space-y-4">
          <Alert variant="info" title="Данные из раздела «Общее»">
            Площадка на лендинге берётся из общих настроек фестиваля. Редактируйте там.
            <div className="mt-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => onNavigateSection("general")}
              >
                Открыть общие настройки
              </Button>
            </div>
          </Alert>
          <div className="grid gap-3 sm:grid-cols-2">
            <ReadOnlyField label="Название площадки" value={competition.venue?.name} />
            <ReadOnlyField label="Адрес" value={competition.venue?.address} />
            <ReadOnlyField label="Город" value={details.city} />
            <ReadOnlyField label="Страна" value={details.country} />
            <ReadOnlyField label="Google Maps" value={details.googleMapsUrl} />
            <ReadOnlyField label="Яндекс Карты" value={details.yandexMapsUrl} />
          </div>
          <ReadOnlyField label="Как добраться" value={details.directions} />
        </div>
      );
    }
    case "JURY":
      return (
        <div className="space-y-3">
          {cards.length === 0 ? (
            <EmptyState title="Нет карточек жюри" description="Добавьте членов жюри." />
          ) : (
            <ul className="space-y-3">
              {cards.map((card, index) => (
                <li key={card.id} className="space-y-2 rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-sm">Карточка {index + 1}</p>
                    {!isReadOnly ? (
                      <IconButton
                        type="button"
                        aria-label="Удалить карточку"
                        variant="ghost"
                        icon={<Trash2 className="size-4" />}
                        onClick={() =>
                          onChange({
                            ...block,
                            cards: cards.filter((item) => item.id !== card.id),
                          })
                        }
                      />
                    ) : null}
                  </div>
                  <LandingImageUploadField
                    label="Фото"
                    value={card.photo}
                    disabled={isReadOnly}
                    uploading={uploading}
                    aspectClassName="aspect-[4/3]"
                    widthClassName="max-w-xs"
                    hint="Кадрируется 4:3 — ровно как в карточке жюри на странице фестиваля."
                    onUpload={async (file) => {
                      const fileReference = await onUploadImage(file);
                      onChange({
                        ...block,
                        cards: cards.map((item) =>
                          item.id === card.id ? { ...item, photo: fileReference } : item,
                        ),
                      });
                    }}
                    onClear={() =>
                      onChange({
                        ...block,
                        cards: cards.map((item) =>
                          item.id === card.id ? { ...item, photo: null } : item,
                        ),
                      })
                    }
                  />
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Input
                      label="Имя"
                      disabled={isReadOnly}
                      value={card.name}
                      onChange={(event) =>
                        onChange({
                          ...block,
                          cards: cards.map((item) =>
                            item.id === card.id ? { ...item, name: event.target.value } : item,
                          ),
                        })
                      }
                    />
                    <Input
                      label="Должность"
                      disabled={isReadOnly}
                      value={card.position ?? ""}
                      onChange={(event) =>
                        onChange({
                          ...block,
                          cards: cards.map((item) =>
                            item.id === card.id ? { ...item, position: event.target.value } : item,
                          ),
                        })
                      }
                    />
                  </div>
                  <Textarea
                    label="Описание"
                    disabled={isReadOnly}
                    value={card.description ?? ""}
                    onChange={(event) =>
                      onChange({
                        ...block,
                        cards: cards.map((item) =>
                          item.id === card.id ? { ...item, description: event.target.value } : item,
                        ),
                      })
                    }
                  />
                </li>
              ))}
            </ul>
          )}
          {!isReadOnly ? (
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                onChange({
                  ...block,
                  cards: [...cards, createJuryCard(cards.length)],
                })
              }
            >
              <Plus className="size-4" aria-hidden="true" />
              Добавить карточку
            </Button>
          ) : null}
        </div>
      );
    case "PARTNERS":
      return (
        <div className="space-y-3">
          {partners.length === 0 ? (
            <EmptyState title="Нет партнёров" description="Добавьте логотипы партнёров." />
          ) : (
            <ul className="space-y-3">
              {partners.map((partner, index) => (
                <li key={partner.id} className="space-y-2 rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-sm">Партнёр {index + 1}</p>
                    {!isReadOnly ? (
                      <IconButton
                        type="button"
                        aria-label="Удалить партнёра"
                        variant="ghost"
                        icon={<Trash2 className="size-4" />}
                        onClick={() =>
                          onChange({
                            ...block,
                            partners: partners.filter((item) => item.id !== partner.id),
                          })
                        }
                      />
                    ) : null}
                  </div>
                  <LandingImageUploadField
                    label="Логотип"
                    value={partner.logo}
                    disabled={isReadOnly}
                    uploading={uploading}
                    aspectClassName="aspect-[3/2]"
                    widthClassName="max-w-xs"
                    fit="contain"
                    hint="Логотип показывается целиком, без обрезки — как в плитке партнёров."
                    onUpload={async (file) => {
                      const fileReference = await onUploadImage(file);
                      onChange({
                        ...block,
                        partners: partners.map((item) =>
                          item.id === partner.id ? { ...item, logo: fileReference } : item,
                        ),
                      });
                    }}
                    onClear={() =>
                      onChange({
                        ...block,
                        partners: partners.map((item) =>
                          item.id === partner.id ? { ...item, logo: null } : item,
                        ),
                      })
                    }
                  />
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Input
                      label="Название"
                      disabled={isReadOnly}
                      value={partner.name}
                      onChange={(event) =>
                        onChange({
                          ...block,
                          partners: partners.map((item) =>
                            item.id === partner.id ? { ...item, name: event.target.value } : item,
                          ),
                        })
                      }
                    />
                    <Input
                      label="Сайт"
                      disabled={isReadOnly}
                      value={partner.website ?? ""}
                      onChange={(event) =>
                        onChange({
                          ...block,
                          partners: partners.map((item) =>
                            item.id === partner.id
                              ? { ...item, website: event.target.value }
                              : item,
                          ),
                        })
                      }
                    />
                  </div>
                </li>
              ))}
            </ul>
          )}
          {!isReadOnly ? (
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                onChange({
                  ...block,
                  partners: [...partners, createPartnerCard(partners.length)],
                })
              }
            >
              <Plus className="size-4" aria-hidden="true" />
              Добавить партнёра
            </Button>
          ) : null}
        </div>
      );
    case "GALLERY":
      return (
        <div className="space-y-3">
          {images.length === 0 ? (
            <EmptyState title="Галерея пуста" description="Загрузите изображения." />
          ) : (
            <ul className="space-y-3">
              {images.map((image, index) => (
                <li key={image.id} className="space-y-2 rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-sm">Изображение {index + 1}</p>
                    {!isReadOnly ? (
                      <IconButton
                        type="button"
                        aria-label="Удалить изображение"
                        variant="ghost"
                        icon={<Trash2 className="size-4" />}
                        onClick={() =>
                          onChange({
                            ...block,
                            images: images.filter((item) => item.id !== image.id),
                          })
                        }
                      />
                    ) : null}
                  </div>
                  <LandingImageUploadField
                    label="Фото"
                    value={image.url}
                    disabled={isReadOnly}
                    uploading={uploading}
                    aspectClassName="aspect-[4/3]"
                    widthClassName="max-w-sm"
                    hint="Кадрируется 4:3 — ровно как в галерее на странице фестиваля."
                    onUpload={async (file) => {
                      const fileReference = await onUploadImage(file);
                      onChange({
                        ...block,
                        images: images.map((item) =>
                          item.id === image.id ? { ...item, url: fileReference } : item,
                        ),
                      });
                    }}
                    onClear={() =>
                      onChange({
                        ...block,
                        images: images.filter((item) => item.id !== image.id),
                      })
                    }
                  />
                  <Input
                    label="Подпись"
                    disabled={isReadOnly}
                    value={image.caption ?? ""}
                    onChange={(event) =>
                      onChange({
                        ...block,
                        images: images.map((item) =>
                          item.id === image.id ? { ...item, caption: event.target.value } : item,
                        ),
                      })
                    }
                  />
                </li>
              ))}
            </ul>
          )}
          {!isReadOnly ? (
            <>
              <Button
                type="button"
                variant="outline"
                loading={uploading}
                onClick={() => galleryInputRef.current?.click()}
              >
                <Plus className="size-4" aria-hidden="true" />
                Загрузить изображение
              </Button>
              <input
                ref={galleryInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="sr-only"
                disabled={uploading}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  event.target.value = "";
                  if (!file) return;
                  void (async () => {
                    try {
                      const fileReference = await onUploadImage(file);
                      onChange({
                        ...block,
                        images: [...images, createGalleryImage(images.length, fileReference)],
                      });
                    } catch {
                      toast.error("Не удалось загрузить изображение");
                    }
                  })();
                }}
              />
            </>
          ) : null}
        </div>
      );
    case "FAQ":
      return (
        <div className="space-y-3">
          {faqItems.length === 0 ? (
            <EmptyState title="Нет вопросов" description="Добавьте FAQ." />
          ) : (
            <ul className="space-y-3">
              {faqItems.map((item, index) => (
                <li key={item.id} className="space-y-2 rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-sm">Вопрос {index + 1}</p>
                    {!isReadOnly ? (
                      <IconButton
                        type="button"
                        aria-label="Удалить вопрос"
                        variant="ghost"
                        icon={<Trash2 className="size-4" />}
                        onClick={() =>
                          onChange({
                            ...block,
                            faqItems: faqItems.filter((faq) => faq.id !== item.id),
                          })
                        }
                      />
                    ) : null}
                  </div>
                  <Input
                    label="Вопрос"
                    disabled={isReadOnly}
                    value={item.question}
                    onChange={(event) =>
                      onChange({
                        ...block,
                        faqItems: faqItems.map((faq) =>
                          faq.id === item.id ? { ...faq, question: event.target.value } : faq,
                        ),
                      })
                    }
                  />
                  <Textarea
                    label="Ответ"
                    disabled={isReadOnly}
                    value={item.answer}
                    onChange={(event) =>
                      onChange({
                        ...block,
                        faqItems: faqItems.map((faq) =>
                          faq.id === item.id ? { ...faq, answer: event.target.value } : faq,
                        ),
                      })
                    }
                  />
                </li>
              ))}
            </ul>
          )}
          {!isReadOnly ? (
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                onChange({
                  ...block,
                  faqItems: [...faqItems, createFaqItem(faqItems.length)],
                })
              }
            >
              <Plus className="size-4" aria-hidden="true" />
              Добавить вопрос
            </Button>
          ) : null}
        </div>
      );
    case "CONTENT":
      return (
        <div className="space-y-3">
          <Input
            label="Заголовок"
            disabled={isReadOnly}
            value={block.title ?? ""}
            onChange={(event) => onChange({ ...block, title: event.target.value })}
          />
          <Textarea
            label="Текст"
            disabled={isReadOnly}
            value={block.body ?? ""}
            onChange={(event) => onChange({ ...block, body: event.target.value })}
            rows={6}
          />
        </div>
      );
    case "REGULATION": {
      const current = (competition.regulations ?? []).find((item) => item.isCurrent);
      return (
        <div className="space-y-4">
          <Alert variant="info" title="Данные из раздела «Положение»">
            На лендинге показывается текущее положение фестиваля. Загрузите или обновите его в
            соответствующем разделе. Здесь блоком можно управлять: включить, выключить и
            переставить.
            <div className="mt-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => onNavigateSection("regulations")}
              >
                Открыть положение
              </Button>
            </div>
          </Alert>
          <div className="grid gap-3 sm:grid-cols-2">
            <ReadOnlyField label="Текущее положение" value={current?.title} />
            <ReadOnlyField label="Версия" value={current?.version} />
          </div>
        </div>
      );
    }
    case "DOCUMENTS": {
      const publicDocuments = (competition.documents ?? []).filter(
        (item) => item.published && (item.visibility === "PUBLIC" || item.visibility === "ALL"),
      );
      return (
        <div className="space-y-4">
          <Alert variant="info" title="Данные из раздела «Документы»">
            На лендинге показываются опубликованные документы с видимостью «Публичная страница».
            Управляйте документами в соответствующем разделе; здесь блок можно включить, выключить и
            переставить.
            <div className="mt-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => onNavigateSection("documents")}
              >
                Открыть документы
              </Button>
            </div>
          </Alert>
          {publicDocuments.length === 0 ? (
            <EmptyState
              title="Нет публичных документов"
              description="Добавьте документы с видимостью «Публичная страница», чтобы они появились на лендинге."
            />
          ) : (
            <ul className="space-y-1.5">
              {publicDocuments.map((document) => (
                <li key={document.id} className="text-sm">
                  {document.title}
                </li>
              ))}
            </ul>
          )}
        </div>
      );
    }
    default:
      return <Alert variant="warning" title="Неизвестный тип блока" />;
  }
}

export function PublicInformationSection({
  competition,
  isLoading = false,
  onAutosaveStateChange,
  onNavigateSection,
}: PublicInformationSectionProps): React.JSX.Element {
  const isReadOnly = competition.status === "COMPLETED";
  const updateLanding = useUpdateLandingConfigurationMutation();
  const uploadLandingImage = useUploadLandingImageMutation();

  const effectiveConfig = useMemo(() => resolveLandingConfig(competition), [competition]);
  const [config, setConfig] = useState<_LandingConfig>(effectiveConfig);
  const isDirtyRef = useRef(false);

  useEffect(() => {
    if (isDirtyRef.current) return;
    setConfig(effectiveConfig);
  }, [effectiveConfig]);

  const autosaveTimer = useRef<number | null>(null);
  const saveGeneration = useRef(0);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set());
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<_LandingBlock | null>(null);

  const persistConfig = useCallback(
    async (next: _LandingConfig) => {
      saveGeneration.current += 1;
      const gen = saveGeneration.current;
      onAutosaveStateChange("saving");
      try {
        await updateLanding.mutateAsync({
          competitionId: competition.id,
          payload: landingConfigToPayload(next),
        });
        if (gen === saveGeneration.current) {
          isDirtyRef.current = false;
          onAutosaveStateChange("saved");
        }
      } catch (error) {
        if (gen === saveGeneration.current) {
          onAutosaveStateChange("error");
          const message =
            error instanceof ApiError
              ? (error.problem?.detail ?? "Не удалось сохранить лендинг")
              : "Не удалось сохранить лендинг";
          toast.error(message);
        }
      }
    },
    [competition.id, updateLanding, onAutosaveStateChange],
  );

  const scheduleConfigSave = useCallback(
    (next: _LandingConfig) => {
      if (autosaveTimer.current != null) window.clearTimeout(autosaveTimer.current);
      onAutosaveStateChange("dirty");
      autosaveTimer.current = window.setTimeout(() => {
        void persistConfig(next);
      }, AUTOSAVE_DELAY_MS);
    },
    [persistConfig, onAutosaveStateChange],
  );

  const updateConfigLocal = useCallback(
    (patch: Partial<_LandingConfig> | ((prev: _LandingConfig) => _LandingConfig)) => {
      if (isReadOnly) return;
      isDirtyRef.current = true;
      setConfig((prev) => {
        const next = typeof patch === "function" ? patch(prev) : { ...prev, ...patch };
        scheduleConfigSave(next);
        return next;
      });
    },
    [isReadOnly, scheduleConfigSave],
  );

  const handleUploadImage = useCallback(
    async (file: File): Promise<string> => {
      return uploadLandingImage.mutateAsync({ competitionId: competition.id, file });
    },
    [competition.id, uploadLandingImage],
  );

  useEffect(
    () => () => {
      if (autosaveTimer.current != null) window.clearTimeout(autosaveTimer.current);
    },
    [],
  );

  const blocks = useMemo(() => sortLandingBlocks(config.blocks), [config.blocks]);

  const toggleExpanded = (id: string): void => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const updateBlock = (blockId: string, nextBlock: _LandingBlock): void => {
    updateConfigLocal((prev) => ({
      ...prev,
      blocks: prev.blocks.map((block) => (block.id === blockId ? nextBlock : block)),
    }));
  };

  const addContentBlock = (): void => {
    const draft = createContentBlock(blocks.length);
    updateConfigLocal((prev) => ({
      ...prev,
      blocks: [...prev.blocks, draft],
    }));
    setExpandedIds((prev) => new Set(prev).add(draft.id));
  };

  if (isLoading) return <PublicInformationSkeleton />;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="min-w-0 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold text-lg">Публичная информация</h2>
            <p className="text-muted-foreground text-sm">
              Лендинг для участников до подачи заявки: hero, площадка, жюри и свои разделы.
            </p>
          </div>
          {!isReadOnly ? (
            <Button type="button" onClick={addContentBlock}>
              <Plus className="size-4" aria-hidden="true" />
              Добавить раздел
            </Button>
          ) : null}
        </div>

        {isReadOnly ? (
          <Alert variant="warning" title="Фестиваль в архиве">
            Публичная информация доступна только для просмотра.
          </Alert>
        ) : null}

        {blocks.length === 0 ? (
          <EmptyState
            title="Нет блоков"
            description="Добавьте раздел контента или включите системные блоки."
            action={
              isReadOnly ? undefined : (
                <Button type="button" onClick={addContentBlock}>
                  <Plus className="size-4" aria-hidden="true" />
                  Добавить раздел
                </Button>
              )
            }
          />
        ) : (
          <ul className="space-y-3" aria-label="Блоки лендинга">
            {blocks.map((block) => {
              const isExpanded = expandedIds.has(block.id);
              return (
                <li
                  key={block.id}
                  draggable={!isReadOnly}
                  onDragStart={() => setDraggedId(block.id)}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={() => {
                    if (!draggedId) return;
                    updateConfigLocal((prev) => ({
                      ...prev,
                      blocks: moveLandingBlockBefore(prev.blocks, draggedId, block.id),
                    }));
                    setDraggedId(null);
                  }}
                  className={cn(
                    "rounded-lg border border-border bg-card",
                    draggedId === block.id && "opacity-60",
                  )}
                >
                  <div className="flex items-center gap-2 px-3 py-3">
                    <GripVertical
                      className="size-4 shrink-0 text-muted-foreground"
                      aria-hidden="true"
                    />
                    <button
                      type="button"
                      className="shrink-0 text-muted-foreground transition-transform"
                      aria-expanded={isExpanded}
                      aria-label={isExpanded ? "Свернуть блок" : "Развернуть блок"}
                      onClick={() => toggleExpanded(block.id)}
                    >
                      <ChevronDown
                        className={cn(
                          "size-4 transition-transform duration-200",
                          isExpanded ? "rotate-0" : "-rotate-90",
                        )}
                      />
                    </button>
                    <button
                      type="button"
                      className="min-w-0 flex-1 cursor-pointer bg-transparent p-0 text-left font-medium text-sm"
                      onClick={() => toggleExpanded(block.id)}
                    >
                      <span className="truncate">{blockDisplayTitle(block)}</span>
                    </button>
                    <Switch
                      label="Показывать"
                      size="sm"
                      disabled={isReadOnly}
                      checked={block.enabled}
                      onCheckedChange={(checked) =>
                        updateBlock(block.id, { ...block, enabled: checked })
                      }
                      containerClassName="shrink-0"
                    />
                    {!isReadOnly && !isSystemBlock(block) ? (
                      <IconButton
                        type="button"
                        aria-label="Удалить раздел"
                        variant="ghost"
                        icon={<Trash2 className="size-4" />}
                        onClick={() => setDeleteTarget(block)}
                      />
                    ) : null}
                  </div>
                  {isExpanded ? (
                    <div className="space-y-3 border-border border-t px-3 py-4">
                      <BlockEditor
                        block={block}
                        competition={competition}
                        isReadOnly={isReadOnly}
                        uploading={uploadLandingImage.isPending}
                        onChange={(next) => updateBlock(block.id, next)}
                        onNavigateSection={onNavigateSection}
                        onUploadImage={handleUploadImage}
                      />
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start">
        <LandingStructurePanel config={config} />
        <LandingPreview competition={competition} config={config} />
      </aside>

      <Dialog open={deleteTarget != null} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Удалить раздел?</DialogTitle>
            <DialogDescription>
              «{deleteTarget ? blockDisplayTitle(deleteTarget) : ""}» будет удалён с лендинга.
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
                  blocks: prev.blocks.filter((item) => item.id !== deleteTarget.id),
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
