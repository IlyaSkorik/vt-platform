import { useEffect, useRef } from "react";

import {
  isPublicationRunning,
  type Protocol,
  type PublicationJob,
  usePublicationJob,
} from "@/features/jury-protocols";
import { toast } from "@/shared/ui";

interface PublicationStatusProps {
  protocol: Protocol;
}

/** Чем кончилась доводка, одной строкой — то же, что раньше говорил ответ на публикацию. */
function summary(job: PublicationJob): string {
  const result = job.result;
  if (result == null) {
    return "";
  }
  const parts = [
    `дипломов: ${result.diplomasAwarded}`,
    job.notify ? `писем: ${result.lettersSent}` : "без писем",
  ];
  return parts.join(", ");
}

/**
 * Что стало с дипломами и письмами после того, как страница уже опубликована.
 *
 * Публикация отвечает, как только итоги стали публичными: это решение организатора, и оно
 * обязано отработать при нём. Дипломы же рисуются по одному на каждую награждённую строку
 * (а в коллективе — ещё и на каждого названного участника), так что на номинации в
 * полтораста номеров это минуты, и выпускает их воркер. Экран — единственное место, где
 * эта работа видна: без него организатор знает, что протокол опубликован, и не знает,
 * дошло ли дело до документов.
 *
 * Поэтому здесь три разных сообщения, а не одно:
 *
 * - **идёт** — чтобы не искать дипломы, которых ещё нет, и чтобы было понятно, что вкладку
 *   можно закрыть: работа идёт на сервере, а не в браузере;
 * - **упало** — единственный случай, когда нужно что-то сделать: у части участников есть
 *   результат и нет документа, и починка — это «Опубликовать заново»;
 * - **кончилось** — счётчики той публикации, тихой строкой: они интересны ровно один раз,
 *   но после перезагрузки страницы взять их больше неоткуда.
 */
export function PublicationStatus({ protocol }: PublicationStatusProps): React.JSX.Element | null {
  // Непубликовавшийся протокол не опрашиваем вовсе: доводки у него быть не может.
  const jobQuery = usePublicationJob(protocol.revision > 0 ? protocol.id : null);
  const job = jobQuery.data ?? null;

  // Докладывается тостом только та доводка, которую застали идущей: о прогоне, который
  // кончился вчера, при открытии экрана кричать не о чем — он уже описан строкой ниже.
  const watched = useRef<Set<string>>(new Set());
  const announced = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (job == null) {
      return;
    }
    if (isPublicationRunning(job)) {
      watched.current.add(job.jobId);
      return;
    }
    if (!watched.current.has(job.jobId) || announced.current.has(job.jobId)) {
      return;
    }
    announced.current.add(job.jobId);

    if (job.status === "FAILED") {
      toast.error(`Дипломы выпущены не до конца: ${job.error ?? "ошибка на сервере"}`, {
        duration: 10_000,
      });
      return;
    }
    // Оговорки — до успеха, и предупреждением, а не ошибкой: тосты встают стопкой, последний
    // поверх предыдущих, и успех, отправленный первым, читался бы из-под красной плашки как
    // «не опубликовано». Публикация при этом прошла.
    const result = job.result;
    if (result != null && result.diplomasMissing > 0) {
      toast.warning(
        `Без диплома осталось ${result.diplomasMissing} — проверьте, назначен ли шаблон диплома этого жанра.`,
        { duration: 10_000 },
      );
    }
    if (result != null && job.notify && result.lettersSkipped > 0) {
      toast.warning(`Не отправлено писем: ${result.lettersSkipped} — у заявителя нет e-mail.`, {
        duration: 10_000,
      });
    }
    toast.success(`Дипломы и письма готовы. ${summary(job)}.`);
  }, [job]);

  if (job == null) {
    return null;
  }

  if (isPublicationRunning(job)) {
    return (
      <p className="rounded-lg border border-info/40 bg-info-surface px-3 py-2 text-sm">
        Выпускаем дипломы и письма по ревизии {job.revision}. Итоги уже опубликованы — страницу
        можно закрыть, работа идёт на сервере.
      </p>
    );
  }

  if (job.status === "FAILED") {
    return (
      <p className="rounded-lg border border-danger/40 bg-danger-surface px-3 py-2 text-sm">
        Дипломы по ревизии {job.revision} выпущены не до конца: {job.error ?? "ошибка на сервере"}.
        Нажмите «Опубликовать заново» — повтор дописывает недостающее, а выпущенное не задваивается.
      </p>
    );
  }

  const result = job.result;
  if (result == null) {
    return null;
  }
  return (
    <p className="text-muted-foreground text-sm">
      Ревизия {job.revision}: {summary(job)}
      {result.diplomasMissing > 0 ? ` · без диплома: ${result.diplomasMissing}` : ""}
      {job.notify && result.lettersSkipped > 0 ? ` · без письма: ${result.lettersSkipped}` : ""}
    </p>
  );
}
