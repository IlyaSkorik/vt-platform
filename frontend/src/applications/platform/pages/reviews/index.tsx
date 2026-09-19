import { MessageSquareQuote, Trash2 } from "lucide-react";
import { useState } from "react";

import {
  authorLabel,
  type Review,
  useDeleteReview,
  usePlatformReviews,
} from "@/features/reviews-console";
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
  toast,
} from "@/shared/ui";

function formatMoment(value: string): string {
  return new Date(value).toLocaleString("ru-RU", { dateStyle: "long", timeStyle: "short" });
}

/** Everything the operator needs to settle a complaint about one note. */
function OperatorReviewCard({ review }: { review: Review }): React.JSX.Element {
  const remove = useDeleteReview("platform");
  const [armed, setArmed] = useState(false);

  return (
    <article className="flex flex-col gap-3 rounded-lg border border-border p-4">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium">{authorLabel(review)}</p>
          <p className="text-muted-foreground text-xs">
            {review.organizationName ?? review.organizationId} · {formatMoment(review.submittedAt)}
          </p>
        </div>
        {review.competitionTitle ? (
          <Badge variant="neutral">{review.competitionTitle}</Badge>
        ) : null}
      </header>

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
        {/* The basis on which this is held, printed beside it: a complaint about a
            review is usually a question about exactly this. */}
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

/**
 * `/platform/reviews` — every review on the platform, in one place.
 *
 * The only screen in the console that reads what people wrote rather than what the
 * platform counted, and it exists for one purpose: a complaint about a note — a
 * name that should not be there, a photograph that should not have been taken —
 * has to be settleable by the one party above both the organizer and the author.
 *
 * The search is local to what is already loaded. A server-side filter would be the
 * right answer at ten thousand notes; at the scale this starts from, it would be a
 * round trip in place of a substring.
 */
export function PlatformReviewsPage(): React.JSX.Element {
  const reviews = usePlatformReviews();
  const [query, setQuery] = useState("");

  const needle = query.trim().toLowerCase();
  const shown = (reviews.data ?? []).filter((review) =>
    needle
      ? [review.text, review.authorName, review.organizationName, review.competitionTitle]
          .filter(Boolean)
          .some((field) => String(field).toLowerCase().includes(needle))
      : true,
  );

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
              <MessageSquareQuote className="size-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <CardTitle>Отзывы</CardTitle>
              <CardDescription>
                Всё, что оставили зрители во всех организациях. Нигде не публикуется.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Input
            label="Поиск"
            placeholder="Имя, организация, фестиваль или слово из отзыва"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />

          {reviews.isLoading ? <LoadingState label="Загружаем отзывы…" /> : null}
          {reviews.isError ? (
            <Alert variant="danger" title="Не удалось загрузить отзывы">
              Обновите страницу и попробуйте снова.
            </Alert>
          ) : null}
          {reviews.data && shown.length === 0 ? (
            <EmptyState
              title={needle ? "Ничего не нашлось" : "Отзывов пока нет"}
              description={
                needle
                  ? "Попробуйте другое слово."
                  : "Они появятся, когда организации подключат блок и начнут собирать."
              }
            />
          ) : null}
          {shown.length > 0 ? (
            <div className="flex flex-col gap-3">
              {shown.map((review) => (
                <OperatorReviewCard key={review.id} review={review} />
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
