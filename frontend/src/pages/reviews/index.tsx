import { ImagePlus, X } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router";

import {
  MAX_PHOTOS,
  MAX_TEXT,
  photoProblem,
  usePublicReviewPage,
  useSubmitReview,
} from "@/features/public-reviews";
import { ConsentCheckbox, REVIEW_CONSENT } from "@/shared/consents";
import { useSeo } from "@/shared/seo";
import {
  Alert,
  Button,
  EmptyState,
  Input,
  LoadingState,
  Select,
  Textarea,
  toast,
} from "@/shared/ui";

/** What the festival picker shows when the note is about nothing in particular. */
const NO_FESTIVAL = "none";

/**
 * `/reviews/:slug` — the review form, as reached from a code on a banner.
 *
 * Unauthenticated by design: the slug in the URL is the only input and the only
 * credential. Nobody registers to say thank you.
 *
 * Built for a phone held in a foyer by somebody who is about to leave, which
 * decides everything about the shape of it. One column. One required field — the
 * words. The name is optional and says so, because asking for it is how you stop
 * getting the honest ones. The festival is a picker that may be left alone.
 *
 * The one thing that is not optional is the consent, and it is not pre-ticked: a
 * consent that starts checked is not freely given, whatever the label says.
 */
export function PublicReviewPage(): React.JSX.Element {
  const { slug } = useParams();
  const { data: page, isLoading, isError } = usePublicReviewPage(slug);
  const submit = useSubmitReview(slug ?? "");

  const [text, setText] = useState("");
  const [authorName, setAuthorName] = useState("");
  const [festival, setFestival] = useState(NO_FESTIVAL);
  const [photos, setPhotos] = useState<File[]>([]);
  const [consented, setConsented] = useState(false);
  const [consentError, setConsentError] = useState<string | undefined>(undefined);
  const [sent, setSent] = useState(false);

  // Reachable by anyone with the link, indexed by no one: what people write here
  // is meant for the organizer, not for a search engine.
  useSeo({ title: page?.title ?? "Отзыв", robots: "noindex" });

  if (isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-6">
        <LoadingState label="Загружаем страницу…" />
      </div>
    );
  }

  if (isError || !page) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-6">
        <div className="w-full max-w-md">
          <EmptyState
            title="Страница не найдена"
            description="Проверьте ссылку или отсканируйте код ещё раз."
          />
        </div>
      </div>
    );
  }

  if (sent) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background p-6">
        <div className="w-full max-w-md">
          <EmptyState
            title="Спасибо!"
            description={`Ваш отзыв отправлен организатору${page.organizationName ? ` — ${page.organizationName}` : ""}.`}
          />
        </div>
      </div>
    );
  }

  const addPhotos = (files: FileList | null): void => {
    if (!files) {
      return;
    }
    const accepted: File[] = [];
    for (const file of Array.from(files)) {
      const problem = photoProblem(file);
      if (problem) {
        toast.error(problem);
        continue;
      }
      accepted.push(file);
    }
    setPhotos((current) => {
      const next = [...current, ...accepted];
      if (next.length > MAX_PHOTOS) {
        toast.error(`Можно приложить не больше ${MAX_PHOTOS} фотографий.`);
      }
      return next.slice(0, MAX_PHOTOS);
    });
  };

  const send = (event: React.FormEvent): void => {
    event.preventDefault();
    // Checked here rather than left to the server: the answer is instant, and the
    // server refuses anyway — this is the courteous copy of the same rule.
    if (!consented) {
      setConsentError("Без согласия отзыв отправить нельзя");
      return;
    }
    setConsentError(undefined);
    submit.mutate(
      {
        text: text.trim(),
        authorName,
        competitionId: festival === NO_FESTIVAL ? null : festival,
        photos,
        consentType: REVIEW_CONSENT.code,
        consentVersion: REVIEW_CONSENT.version,
      },
      {
        onSuccess: () => setSent(true),
        onError: (error) => toast.error(error.message || "Не удалось отправить отзыв"),
      },
    );
  };

  const festivalOptions = [
    { value: NO_FESTIVAL, label: "Не указывать" },
    ...page.festivals.map((option) => ({ value: option.id, label: option.title })),
  ];

  return (
    <div className="min-h-svh bg-background">
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-5 px-4 py-6">
        <header className="flex flex-col gap-2">
          {page.organizationName ? (
            <p className="text-muted-foreground text-sm">{page.organizationName}</p>
          ) : null}
          <h1 className="font-semibold text-2xl leading-tight">{page.title}</h1>
          {page.intro ? <p className="text-muted-foreground text-sm">{page.intro}</p> : null}
        </header>

        {page.accepting ? (
          <form className="flex flex-col gap-5" onSubmit={send}>
            <Textarea
              label="Ваш отзыв"
              required
              rows={6}
              maxLength={MAX_TEXT}
              value={text}
              placeholder="Что вам запомнилось?"
              onChange={(event) => setText(event.target.value)}
            />

            <Input
              label="Как вас зовут"
              hint="Можно не указывать — отзыв примем и без подписи."
              value={authorName}
              maxLength={120}
              onChange={(event) => setAuthorName(event.target.value)}
            />

            {page.festivals.length > 0 ? (
              <Select
                label="О каком фестивале отзыв"
                options={festivalOptions}
                value={festival}
                onValueChange={setFestival}
              />
            ) : null}

            <div className="flex flex-col gap-2">
              <span className="font-medium text-sm">Фотографии</span>
              {photos.length > 0 ? (
                <ul className="flex flex-col gap-1">
                  {photos.map((photo) => (
                    <li
                      key={`${photo.name}-${photo.size}-${photo.lastModified}`}
                      className="flex items-center justify-between gap-2 rounded-md border border-border px-3 py-2 text-sm"
                    >
                      <span className="min-w-0 truncate">{photo.name}</span>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        aria-label={`Убрать ${photo.name}`}
                        onClick={() =>
                          setPhotos((current) => current.filter((item) => item !== photo))
                        }
                      >
                        <X className="size-4" />
                      </Button>
                    </li>
                  ))}
                </ul>
              ) : null}
              {photos.length < MAX_PHOTOS ? (
                <label className="inline-flex w-fit cursor-pointer items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-muted/50">
                  <ImagePlus className="size-4" />
                  Добавить фотографию
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    className="sr-only"
                    onChange={(event) => {
                      addPhotos(event.target.files);
                      // Cleared so picking the same file twice still fires a change.
                      event.target.value = "";
                    }}
                  />
                </label>
              ) : null}
              <p className="text-muted-foreground text-xs">
                До {MAX_PHOTOS} фотографий, каждая до 8 МБ. Не обязательно.
              </p>
            </div>

            <ConsentCheckbox
              consent={REVIEW_CONSENT}
              checked={consented}
              onChange={(next) => {
                setConsented(next);
                if (next) {
                  setConsentError(undefined);
                }
              }}
              error={consentError}
            />

            <Button type="submit" loading={submit.isPending} disabled={!text.trim()}>
              Отправить отзыв
            </Button>
          </form>
        ) : (
          <Alert variant="info" title="Приём отзывов закрыт">
            Организатор больше не собирает отзывы по этой ссылке. Спасибо, что зашли.
          </Alert>
        )}
      </div>
    </div>
  );
}
