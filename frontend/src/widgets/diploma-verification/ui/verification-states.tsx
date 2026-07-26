import { RotateCcw, X } from "lucide-react";
import { Button, Card, CardContent, Skeleton } from "@/shared/ui";
import { RegistrySeal } from "./registry-seal";

/** Waiting on the register — the confirmed layout's own shape, so nothing jumps. */
export function VerificationSkeleton(): React.JSX.Element {
  return (
    <div className="space-y-6" aria-busy="true">
      <Card className="items-center gap-5 px-6 py-9 sm:py-11">
        <Skeleton variant="circle" className="size-28" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-5 w-80 max-w-full" />
      </Card>
      <Card>
        <CardContent className="space-y-5 px-6 py-6 sm:px-8">
          {["a", "b", "c", "d", "e", "f"].map((key) => (
            <div key={key} className="grid gap-2 sm:grid-cols-[11rem_1fr] sm:gap-6">
              <Skeleton className="h-3.5 w-28" />
              <Skeleton className="h-5 w-2/3" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * The register holds no such document.
 *
 * Says nothing technical and nothing about *why*: unknown, malformed and revoked
 * tokens are one and the same answer, and the backend does not distinguish them
 * either. It closes with the one action that can actually help — ask the organizers.
 */
export function VerificationNotFound(): React.JSX.Element {
  return (
    <Card className="items-center gap-5 border-danger/20 px-6 py-9 text-center sm:px-10 sm:py-11">
      <RegistrySeal tone="rejected">
        <X strokeWidth={3} />
      </RegistrySeal>
      <div className="space-y-3">
        <h2 className="font-bold text-2xl text-foreground tracking-tight sm:text-3xl">
          Диплом не найден
        </h2>
        <p className="mx-auto max-w-md text-balance text-base text-foreground/80">
          Мы не смогли подтвердить подлинность данного диплома.
        </p>
        <p className="mx-auto max-w-md text-balance text-muted-foreground text-sm">
          Проверьте QR-код или обратитесь к организаторам конкурса.
        </p>
      </div>
    </Card>
  );
}

interface VerificationUnavailableProps {
  onRetry: () => void;
  retrying?: boolean;
}

/**
 * The register could not be reached.
 *
 * Kept strictly separate from "Диплом не найден": a connection failure says
 * nothing about a document's authenticity, and reporting it as a failed check
 * would tell the holder of a genuine diploma that theirs is a forgery. Stated in
 * the register's own language — no status codes, no diagnostics — with the only
 * useful action attached.
 */
export function VerificationUnavailable({
  onRetry,
  retrying = false,
}: VerificationUnavailableProps): React.JSX.Element {
  return (
    <Card className="items-center gap-4 px-6 py-9 text-center sm:px-10">
      <div className="space-y-2">
        <h2 className="font-semibold text-foreground text-xl tracking-tight">
          Реестр временно недоступен
        </h2>
        <p className="mx-auto max-w-md text-balance text-muted-foreground text-sm">
          Не удалось связаться с реестром документов. Проверьте подключение и попробуйте снова.
        </p>
      </div>
      <Button
        onClick={onRetry}
        loading={retrying}
        size="lg"
        leftIcon={<RotateCcw aria-hidden="true" />}
      >
        Повторить проверку
      </Button>
    </Card>
  );
}
