import { Copy, Download, MessageSquareQuote, Trash2 } from "lucide-react";
import { useState } from "react";

import {
  authorLabel,
  OPEN_LINK_NOTE,
  publicReviewUrl,
  type Review,
  useDeleteReview,
  useReviewPage,
  useReviews,
  useUpdateReviewPage,
} from "@/features/reviews-console";
import { apiClient } from "@/shared/api";
import {
  Alert,
  Badge,
  Button,
  EmptyState,
  Input,
  LoadingState,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageSection,
  PageTitle,
  Switch,
  Textarea,
  toast,
} from "@/shared/ui";

/**
 * Put the review link on the clipboard.
 *
 * This address goes onto a banner and into a chat, and retyping a ten-character
 * slug by eye is exactly how a foyer ends up at a 404. Refusal is possible (an
 * insecure origin, a denied permission), and showing the URL is a worse experience
 * than copying it and a better one than silence.
 */
async function copyLink(link: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(link);
    toast.success("Ссылка скопирована");
  } catch {
    toast.error(`Не удалось скопировать. Ссылка: ${link}`);
  }
}

/** Fetch the QR through the API client, so the auth header travels with it. */
async function downloadQr(slug: string): Promise<void> {
  const blob = await apiClient("staff/reviews/page/qr.png").blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `qr-reviews-${slug}.png`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function formatMoment(value: string): string {
  return new Date(value).toLocaleString("ru-RU", { dateStyle: "long", timeStyle: "short" });
}

/** One note, printed as the organizer reads it: who, when, about what, and what they said. */
function ReviewCard({ review }: { review: Review }): React.JSX.Element {
  const remove = useDeleteReview("staff");
  const [armed, setArmed] = useState(false);

  return (
    <article className="flex flex-col gap-3 rounded-lg border border-border p-4">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium">{authorLabel(review)}</p>
          <p className="text-muted-foreground text-xs">{formatMoment(review.submittedAt)}</p>
        </div>
        {review.competitionTitle ? (
          <Badge variant="neutral">{review.competitionTitle}</Badge>
        ) : null}
      </header>

      {/* `whitespace-pre-line`: somebody thanking three people put each on its own
          line, and collapsing that into a paragraph rewrites what they said. */}
      <p className="whitespace-pre-line text-sm leading-6">{review.text}</p>

      {review.photos.length > 0 ? (
        <ul className="flex flex-wrap gap-2">
          {review.photos.map((photo) => (
            <li key={photo}>
              <a href={photo} target="_blank" rel="noopener">
                <img
                  src={photo}
                  alt="Фотография из отзыва"
                  loading="lazy"
                  className="size-24 rounded-md object-cover"
                />
              </a>
            </li>
          ))}
        </ul>
      ) : null}

      <footer className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-muted-foreground text-xs">
          Согласие {review.consentType} ред. {review.consentVersion} ·{" "}
          {formatMoment(review.consentAcceptedAt)}
        </p>
        <Button
          size="sm"
          variant={armed ? "danger" : "ghost"}
          loading={remove.isPending}
          onClick={() => {
            if (!armed) {
              setArmed(true);
              return;
            }
            remove.mutate(review.id, {
              onSuccess: () => toast.success("Отзыв удалён"),
              onError: (error) => toast.error(error.message || "Не удалось удалить отзыв"),
            });
          }}
        >
          <Trash2 className="size-4" />
          {armed ? "Подтвердить удаление" : "Удалить"}
        </Button>
      </footer>
    </article>
  );
}

/** The link, the code and the wording — everything that ends up on the banner. */
function PageSettings({ slug }: { slug: string }): React.JSX.Element {
  const page = useReviewPage();
  const update = useUpdateReviewPage();
  const [title, setTitle] = useState(page.data?.title ?? "");
  const [intro, setIntro] = useState(page.data?.intro ?? "");
  const link = publicReviewUrl(slug);

  const save = (event: React.FormEvent): void => {
    event.preventDefault();
    update.mutate(
      { title: title.trim(), intro: intro.trim() },
      {
        onSuccess: () => toast.success("Страница обновлена"),
        onError: (error) => toast.error(error.message || "Не удалось сохранить"),
      },
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2 rounded-lg border border-border p-4">
        <p className="font-medium text-sm">Ссылка для баннера</p>
        <p className="break-all font-mono text-sm">{link}</p>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={() => void copyLink(link)}>
            <Copy className="size-4" />
            Скопировать ссылку
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void downloadQr(slug)}>
            <Download className="size-4" />
            Скачать QR-код
          </Button>
        </div>
        <p className="text-muted-foreground text-xs">
          Ссылка постоянная: баннер печатают один раз, и она не меняется.
        </p>
      </div>

      <form className="flex flex-col gap-3" onSubmit={save}>
        <Input
          label="Заголовок страницы"
          value={title}
          maxLength={200}
          onChange={(event) => setTitle(event.target.value)}
        />
        <Textarea
          label="Текст под заголовком"
          hint="Не обязателен — страница понятна и без него."
          rows={3}
          maxLength={1000}
          value={intro}
          onChange={(event) => setIntro(event.target.value)}
        />
        <Button type="submit" loading={update.isPending} className="w-fit">
          Сохранить
        </Button>
      </form>
    </div>
  );
}

/**
 * `/staff/reviews` — the organizer's side of the reviews block.
 *
 * Two things on one screen, in the order they are needed: the link and the code
 * that go onto the banner, and then what came back through them.
 *
 * Nothing here is moderation, because nothing collected here is published. The
 * only action on a note is removing it, which is what a complaint actually calls
 * for; approving one would be a workflow whose only effect is to enable the next
 * step of itself.
 */
export function StaffReviewsPage(): React.JSX.Element {
  const page = useReviewPage();
  const reviews = useReviews();
  const update = useUpdateReviewPage();

  return (
    <PageContainer>
      <PageHeader>
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
            <MessageSquareQuote className="size-5" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <PageTitle>Отзывы</PageTitle>
            <PageDescription>
              Код на баннере ведёт на страницу, где зритель оставляет отзыв.
            </PageDescription>
          </div>
        </div>
      </PageHeader>
      <PageContent>
        <PageSection
          title="Страница отзывов"
          description="Адрес, QR-код и то, что человек увидит после сканирования."
        >
          {page.isLoading ? <LoadingState label="Загружаем страницу…" /> : null}
          {page.isError ? (
            <Alert variant="danger" title="Не удалось загрузить страницу отзывов">
              Обновите страницу и попробуйте снова.
            </Alert>
          ) : null}
          {page.data ? (
            <div className="flex flex-col gap-4">
              <Alert variant="info" title="Как это работает">
                {OPEN_LINK_NOTE}
              </Alert>
              <div className="flex items-center justify-between gap-3 rounded-lg border border-border p-4">
                <div className="min-w-0">
                  <p className="font-medium text-sm">Приём отзывов</p>
                  <p className="text-muted-foreground text-xs">
                    Выключите, когда закончите собирать: ссылка продолжит работать и объяснит, что
                    приём закрыт.
                  </p>
                </div>
                <Switch
                  checked={page.data.accepting}
                  disabled={update.isPending}
                  onCheckedChange={(next) =>
                    update.mutate(
                      { accepting: next },
                      {
                        onError: (error) =>
                          toast.error(error.message || "Не удалось переключить приём"),
                      },
                    )
                  }
                />
              </div>
              <PageSettings slug={page.data.slug} />
            </div>
          ) : null}
        </PageSection>

        <PageSection
          title="Что оставили"
          description={
            page.data ? `Всего отзывов: ${page.data.reviewCount}.` : "Отзывы со страницы."
          }
        >
          {reviews.isLoading ? <LoadingState label="Загружаем отзывы…" /> : null}
          {reviews.isError ? (
            <Alert variant="danger" title="Не удалось загрузить отзывы">
              Обновите страницу и попробуйте снова.
            </Alert>
          ) : null}
          {reviews.data?.length === 0 ? (
            <EmptyState
              title="Пока ничего"
              description="Отзывы появятся здесь, как только кто-нибудь отсканирует код."
            />
          ) : null}
          {reviews.data && reviews.data.length > 0 ? (
            <div className="flex flex-col gap-3">
              {reviews.data.map((review) => (
                <ReviewCard key={review.id} review={review} />
              ))}
            </div>
          ) : null}
        </PageSection>
      </PageContent>
    </PageContainer>
  );
}
