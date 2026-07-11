import { Tags } from "lucide-react";
import { Card, Skeleton } from "@/shared/ui";

export function AgeCategoriesSkeleton(): React.JSX.Element {
  return (
    <div
      role="status"
      aria-label="Загрузка возрастных категорий"
      className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]"
    >
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-10 w-full" />
        <div className="space-y-3">
          {["nom-a", "nom-b"].map((key) => (
            <Card key={key} className="shadow-none">
              <div className="space-y-2 p-4">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-4 w-4 rounded" />
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="ml-auto h-5 w-20 rounded-full" />
                </div>
                <div className="space-y-2 pl-7">
                  <Skeleton className="h-8 w-full rounded-md" />
                  <Skeleton className="h-8 w-full rounded-md" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
      <Card className="shadow-none">
        <div className="space-y-3 p-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Tags className="size-4" aria-hidden="true" />
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-20 w-full" />
        </div>
      </Card>
    </div>
  );
}
