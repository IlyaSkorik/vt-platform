import { ClipboardCheck } from "lucide-react";
import { Card, Skeleton } from "@/shared/ui";

export function ParticipationFormatsSkeleton(): React.JSX.Element {
  return (
    <div
      role="status"
      aria-label="Загрузка форматов участия"
      className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]"
    >
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-10 w-full" />
        <div className="grid gap-3 sm:grid-cols-2">
          {["card-a", "card-b", "card-c", "card-d"].map((key) => (
            <Card key={key} className="shadow-none">
              <div className="space-y-3 p-4">
                <div className="flex items-center gap-2">
                  <Skeleton className="h-4 w-4 rounded" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
                <Skeleton className="h-5 w-24 rounded-full" />
                <Skeleton className="h-10 w-full" />
                <div className="flex gap-2">
                  <Skeleton className="h-8 w-8 rounded-md" />
                  <Skeleton className="h-8 w-8 rounded-md" />
                  <Skeleton className="h-8 w-8 rounded-md" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
      <Card className="shadow-none">
        <div className="space-y-3 p-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <ClipboardCheck className="size-4" aria-hidden="true" />
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-24 w-full" />
        </div>
      </Card>
    </div>
  );
}
