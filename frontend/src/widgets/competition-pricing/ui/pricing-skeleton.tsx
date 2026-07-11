import { CircleDollarSign } from "lucide-react";
import { Card, Skeleton } from "@/shared/ui";

export function PricingSkeleton(): React.JSX.Element {
  return (
    <div
      role="status"
      aria-label="Загрузка цен"
      className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]"
    >
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-10 w-full" />
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {["a", "b", "c", "d", "e", "f"].map((key) => (
            <Card key={key} className="shadow-none">
              <div className="space-y-3 p-4">
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-3 w-1/2" />
                <Skeleton className="h-3 w-3/5" />
                <Skeleton className="h-9 w-full" />
              </div>
            </Card>
          ))}
        </div>
      </div>
      <Card className="shadow-none">
        <div className="space-y-3 p-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <CircleDollarSign className="size-4" aria-hidden="true" />
            <Skeleton className="h-4 w-32" />
          </div>
          <Skeleton className="h-32 w-full" />
        </div>
      </Card>
    </div>
  );
}
