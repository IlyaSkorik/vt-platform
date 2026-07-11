import { FileText } from "lucide-react";
import { Card, Skeleton } from "@/shared/ui";

export function DocumentsSkeleton(): React.JSX.Element {
  return (
    <div
      role="status"
      aria-label="Загрузка документов"
      className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]"
    >
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-24 w-full" />
        <div className="space-y-3">
          {["a", "b", "c"].map((key) => (
            <Card key={key} className="shadow-none">
              <div className="flex items-start gap-3 p-4">
                <Skeleton className="size-10 rounded-md" />
                <div className="min-w-0 flex-1 space-y-2">
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-3 w-3/4" />
                  <Skeleton className="h-3 w-1/3" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
      <Card className="shadow-none">
        <div className="space-y-3 p-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <FileText className="size-4" aria-hidden="true" />
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-20 w-full" />
        </div>
      </Card>
    </div>
  );
}
