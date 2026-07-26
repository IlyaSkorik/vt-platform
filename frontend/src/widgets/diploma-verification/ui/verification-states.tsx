import { Frown, RotateCcw, ScanLine } from "lucide-react";
import { Button, Card, CardContent, EmptyState, Skeleton } from "@/shared/ui";

/** Waiting on the verification read — one card-shaped placeholder, no layout jump. */
export function VerificationSkeleton(): React.JSX.Element {
  return (
    <Card aria-busy="true">
      <CardContent className="space-y-6 py-6">
        <Skeleton className="h-7 w-56" />
        <div className="space-y-4">
          {["a", "b", "c", "d", "e", "f"].map((key) => (
            <div key={key} className="space-y-2">
              <Skeleton className="h-3.5 w-24" />
              <Skeleton className="h-5 w-2/3" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * The token matches no diploma (404).
 *
 * Deliberately says nothing about *why* — unknown, malformed and revoked tokens
 * are one and the same answer here, and the backend does not distinguish them
 * either.
 */
export function VerificationNotFound(): React.JSX.Element {
  return (
    <Card>
      <CardContent className="py-4">
        <EmptyState
          icon={<ScanLine aria-hidden="true" />}
          title="Диплом не найден"
          description="Проверьте QR-код или номер диплома."
        />
      </CardContent>
    </Card>
  );
}

interface VerificationErrorProps {
  onRetry: () => void;
  retrying?: boolean;
}

/**
 * The read failed for a reason other than 404 — offer a retry.
 *
 * Kept distinct from "не найден" on purpose: a network blip must never be shown
 * as a failed authenticity check.
 */
export function VerificationError({
  onRetry,
  retrying = false,
}: VerificationErrorProps): React.JSX.Element {
  return (
    <Card>
      <CardContent className="py-4">
        <EmptyState
          icon={<Frown aria-hidden="true" />}
          title="Не удалось проверить диплом"
          description="Что-то пошло не так при загрузке. Проверьте соединение и попробуйте снова."
          action={
            <Button
              onClick={onRetry}
              loading={retrying}
              leftIcon={<RotateCcw aria-hidden="true" />}
            >
              Повторить
            </Button>
          }
        />
      </CardContent>
    </Card>
  );
}
