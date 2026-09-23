import { useMemo, useState } from "react";
import {
  blockDisplayTitle,
  resolveContactsConfig,
  resolveMediaUrl,
  sortLandingBlocks,
} from "@/features/competitions";
import type {
  _LandingBlock,
  _LandingConfig,
  CompetitionDetail,
} from "@/shared/api/generated/model-competitions";
import { cn } from "@/shared/lib";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/shared/ui";

type PreviewViewport = "desktop" | "tablet" | "mobile";

const VIEWPORT_WIDTH: Record<PreviewViewport, string> = {
  desktop: "100%",
  tablet: "48rem",
  mobile: "23.5rem",
};

interface LandingPreviewProps {
  competition: CompetitionDetail;
  config: _LandingConfig;
}

function PreviewHero({ block }: { block: _LandingBlock }): React.JSX.Element {
  const coverUrl = resolveMediaUrl(block.coverImage);
  return (
    <section className="space-y-2 border-border border-b pb-4">
      <div
        className={cn(
          "flex h-28 items-center justify-center rounded-md bg-muted text-muted-foreground text-xs",
          coverUrl && "bg-cover bg-center",
        )}
        style={coverUrl ? { backgroundImage: `url(${coverUrl})` } : undefined}
      >
        {coverUrl ? null : "Обложка"}
      </div>
      <h3 className="font-semibold text-base">{block.title?.trim() || "Без заголовка"}</h3>
      {block.subtitle?.trim() ? (
        <p className="text-muted-foreground text-sm">{block.subtitle}</p>
      ) : null}
    </section>
  );
}

function PreviewRegulation({ competition }: { competition: CompetitionDetail }): React.JSX.Element {
  const current = (competition.regulations ?? []).find((item) => item.isCurrent);
  return (
    <section className="space-y-1 border-border border-b pb-4">
      <h3 className="font-semibold text-sm">Положение фестиваля</h3>
      <p className="text-muted-foreground text-sm">
        {current ? current.title : "Положение ещё не загружено"}
      </p>
    </section>
  );
}

function PreviewDocuments({ competition }: { competition: CompetitionDetail }): React.JSX.Element {
  const documents = (competition.documents ?? []).filter(
    (item) => item.published && (item.visibility === "PUBLIC" || item.visibility === "ALL"),
  );
  return (
    <section className="space-y-1 border-border border-b pb-4">
      <h3 className="font-semibold text-sm">Документы</h3>
      {documents.length > 0 ? (
        documents.map((document) => (
          <p key={document.id} className="text-muted-foreground text-sm">
            {document.title}
          </p>
        ))
      ) : (
        <p className="text-muted-foreground text-sm">Нет публичных документов</p>
      )}
    </section>
  );
}

function PreviewVenue({ competition }: { competition: CompetitionDetail }): React.JSX.Element {
  const contacts = resolveContactsConfig(competition);
  const venue = competition.venue;
  const details = contacts.venueDetails;
  const lines = [
    venue?.name,
    venue?.address,
    [details.city, details.country].filter(Boolean).join(", ") || null,
    details.directions,
  ].filter((line): line is string => Boolean(line?.trim()));

  return (
    <section className="space-y-1 border-border border-b pb-4">
      <h3 className="font-semibold text-sm">Площадка</h3>
      {lines.length > 0 ? (
        lines.map((line) => (
          <p key={line} className="text-muted-foreground text-sm">
            {line}
          </p>
        ))
      ) : (
        <p className="text-muted-foreground text-sm">Данные площадки не заполнены</p>
      )}
    </section>
  );
}

function PreviewJury({ block }: { block: _LandingBlock }): React.JSX.Element {
  const cards = block.cards ?? [];
  return (
    <section className="space-y-2 border-border border-b pb-4">
      <h3 className="font-semibold text-sm">{blockDisplayTitle(block)}</h3>
      {cards.length === 0 ? (
        <p className="text-muted-foreground text-sm">Нет карточек жюри</p>
      ) : (
        <ul className="space-y-2">
          {cards.map((card) => {
            const photoUrl = resolveMediaUrl(card.photo);
            return (
              <li
                key={card.id}
                className="flex items-center gap-2 rounded-md border border-border px-3 py-2"
              >
                {photoUrl ? (
                  <img
                    src={photoUrl}
                    alt=""
                    className="aspect-[4/3] w-14 shrink-0 rounded object-cover"
                  />
                ) : (
                  <div className="aspect-[4/3] w-14 shrink-0 rounded bg-muted" />
                )}
                <div className="min-w-0">
                  <p className="font-medium text-sm">{card.name || "Без имени"}</p>
                  {card.position ? (
                    <p className="text-muted-foreground text-xs">{card.position}</p>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function PreviewPartners({ block }: { block: _LandingBlock }): React.JSX.Element {
  const partners = block.partners ?? [];
  return (
    <section className="space-y-2 border-border border-b pb-4">
      <h3 className="font-semibold text-sm">{blockDisplayTitle(block)}</h3>
      {partners.length === 0 ? (
        <p className="text-muted-foreground text-sm">Нет партнёров</p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {partners.map((partner) => {
            const logoUrl = resolveMediaUrl(partner.logo);
            return (
              <li key={partner.id} className="flex items-center gap-2">
                {logoUrl ? (
                  <img src={logoUrl} alt="" className="size-8 rounded object-contain" />
                ) : null}
                <Badge variant="secondary" size="sm">
                  {partner.name || "Партнёр"}
                </Badge>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function PreviewGallery({ block }: { block: _LandingBlock }): React.JSX.Element {
  const images = block.images ?? [];
  return (
    <section className="space-y-2 border-border border-b pb-4">
      <h3 className="font-semibold text-sm">{blockDisplayTitle(block)}</h3>
      {images.length === 0 ? (
        <p className="text-muted-foreground text-sm">Нет изображений</p>
      ) : (
        <ul className="grid grid-cols-2 gap-2">
          {images.map((image) => {
            const url = resolveMediaUrl(image.url);
            return (
              <li
                key={image.id}
                className="flex aspect-[4/3] items-center justify-center overflow-hidden rounded-md bg-muted text-muted-foreground text-xs"
              >
                {url ? (
                  <img src={url} alt={image.caption ?? ""} className="size-full object-cover" />
                ) : (
                  image.caption?.trim() || "Фото"
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function PreviewFaq({ block }: { block: _LandingBlock }): React.JSX.Element {
  const faqItems = block.faqItems ?? [];
  return (
    <section className="space-y-2 border-border border-b pb-4">
      <h3 className="font-semibold text-sm">{blockDisplayTitle(block)}</h3>
      {faqItems.length === 0 ? (
        <p className="text-muted-foreground text-sm">Нет вопросов</p>
      ) : (
        <ul className="space-y-2">
          {faqItems.map((item) => (
            <li key={item.id} className="space-y-0.5">
              <p className="font-medium text-sm">{item.question || "Вопрос"}</p>
              <p className="text-muted-foreground text-xs">{item.answer || "Ответ"}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function PreviewContent({ block }: { block: _LandingBlock }): React.JSX.Element {
  return (
    <section className="space-y-1 border-border border-b pb-4 last:border-b-0 last:pb-0">
      <h3 className="font-semibold text-sm">{blockDisplayTitle(block)}</h3>
      <p className="whitespace-pre-wrap text-muted-foreground text-sm">
        {block.body?.trim() || "Пустой раздел"}
      </p>
    </section>
  );
}

function PreviewBlock({
  block,
  competition,
}: {
  block: _LandingBlock;
  competition: CompetitionDetail;
}): React.JSX.Element | null {
  switch (block.type) {
    case "HERO":
      return <PreviewHero block={block} />;
    case "REGULATION":
      return <PreviewRegulation competition={competition} />;
    case "DOCUMENTS":
      return <PreviewDocuments competition={competition} />;
    case "VENUE":
      return <PreviewVenue competition={competition} />;
    case "JURY":
      return <PreviewJury block={block} />;
    case "PARTNERS":
      return <PreviewPartners block={block} />;
    case "GALLERY":
      return <PreviewGallery block={block} />;
    case "FAQ":
      return <PreviewFaq block={block} />;
    case "CONTENT":
      return <PreviewContent block={block} />;
    default:
      return null;
  }
}

export function LandingPreview({ competition, config }: LandingPreviewProps): React.JSX.Element {
  const [viewport, setViewport] = useState<PreviewViewport>("desktop");
  const enabledBlocks = useMemo(
    () => sortLandingBlocks(config.blocks).filter((block) => block.enabled),
    [config.blocks],
  );

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Предпросмотр</CardTitle>
        <CardDescription>Как увидят участники на лендинге</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <fieldset className="flex flex-wrap gap-1 border-0 p-0">
          <legend className="sr-only">Ширина предпросмотра</legend>
          {(
            [
              ["desktop", "Desktop"],
              ["tablet", "Tablet"],
              ["mobile", "Mobile"],
            ] as const
          ).map(([id, label]) => (
            <Button
              key={id}
              type="button"
              size="sm"
              variant={viewport === id ? "primary" : "outline"}
              onClick={() => setViewport(id)}
            >
              {label}
            </Button>
          ))}
        </fieldset>
        <div className="overflow-x-auto rounded-lg border border-border bg-muted/20 p-3">
          <div
            className="mx-auto space-y-4 rounded-md border border-border bg-card p-4 transition-[max-width]"
            style={{ maxWidth: VIEWPORT_WIDTH[viewport], width: "100%" }}
          >
            {enabledBlocks.length === 0 ? (
              <p className="text-muted-foreground text-sm">Нет включённых блоков</p>
            ) : (
              enabledBlocks.map((block) => (
                <PreviewBlock key={block.id} block={block} competition={competition} />
              ))
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
