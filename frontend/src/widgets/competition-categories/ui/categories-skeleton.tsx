import { FolderTree } from "lucide-react";
import { Card, Skeleton } from "@/shared/ui";

export function CategoriesSkeleton(): React.JSX.Element {
  return (
    <div
      role="status"
      aria-label="Загрузка жанров"
      className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]"
    >
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-24 w-full" />
        <div className="space-y-3">
          {["cat-a", "cat-b", "cat-c"].map((key) => (
            <Card key={key} className="shadow-none">
              <div className="space-y-3 p-4">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-5 w-5 rounded" />
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="ml-auto h-5 w-12 rounded-full" />
                </div>
                <Skeleton className="h-3 w-2/3" />
                <div className="space-y-2 pl-8">
                  <Skeleton className="h-3 w-1/2" />
                  <Skeleton className="h-3 w-2/5" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
      <Card className="shadow-none">
        <div className="space-y-3 p-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <FolderTree className="size-4" aria-hidden="true" />
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-20 w-full" />
        </div>
      </Card>
    </div>
  );
}
