import { TriangleAlert } from "lucide-react";
import { cn } from "@/shared/lib";
import { Button, Card, CardContent, CardHeader, CardTitle, EmptyState } from "@/shared/ui";
import type { WidgetStatus } from "../../model";

export interface WidgetCardProps {
  /** Section heading rendered in the card header. */
  title: string;
  /** Optional trailing header slot (e.g. a "view all" link or unread badge). */
  headerAction?: React.ReactNode;
  status: WidgetStatus;
  /** Skeleton shown while `status === "loading"`. */
  loadingSkeleton: React.ReactNode;
  /** Copy for the empty state. */
  emptyTitle: string;
  emptyDescription?: string;
  /** Icon for the empty state (defaults to the shared inbox glyph). */
  emptyIcon?: React.ReactNode;
  /** Retry handler surfaced in the error state. */
  onRetry?: () => void;
  /** Success content — rendered only when `status === "success"`. */
  children: React.ReactNode;
  className?: string;
  /** Accessible label for the region; falls back to `title`. */
  ariaLabel?: string;
}

/**
 * WidgetCard — the shared shell every list-style dashboard widget composes.
 *
 * It owns the four-state contract (loading / error / empty / success) so each
 * widget only supplies its skeleton and its success body. Rendered as a
 * labelled region (landmark) with a heading, keeping the dashboard navigable by
 * assistive tech. Pure composition of `shared/ui` primitives; token-only.
 */
export function WidgetCard({
  title,
  headerAction,
  status,
  loadingSkeleton,
  emptyTitle,
  emptyDescription,
  emptyIcon,
  onRetry,
  children,
  className,
  ariaLabel,
}: WidgetCardProps): React.JSX.Element {
  return (
    <Card
      aria-label={ariaLabel ?? title}
      aria-busy={status === "loading"}
      className={cn("h-full", className)}
    >
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
        {headerAction}
      </CardHeader>
      <CardContent className="flex-1">
        {status === "loading" && loadingSkeleton}

        {status === "error" && (
          <EmptyState
            icon={<TriangleAlert className="text-danger" />}
            title="Не удалось загрузить данные"
            description="Произошла ошибка при обращении к сервису. Попробуйте ещё раз."
            {...(onRetry
              ? {
                  action: (
                    <Button variant="outline" size="sm" onClick={onRetry}>
                      Повторить
                    </Button>
                  ),
                }
              : {})}
          />
        )}

        {status === "empty" && (
          <EmptyState
            {...(emptyIcon ? { icon: emptyIcon } : {})}
            title={emptyTitle}
            {...(emptyDescription ? { description: emptyDescription } : {})}
          />
        )}

        {status === "success" && children}
      </CardContent>
    </Card>
  );
}
