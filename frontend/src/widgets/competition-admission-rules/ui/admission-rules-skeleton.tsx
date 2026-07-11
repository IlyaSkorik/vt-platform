import { ShieldCheck } from "lucide-react";
import { Card, Skeleton } from "@/shared/ui";

export function AdmissionRulesSkeleton(): React.JSX.Element {
  return (
    <div
      role="status"
      aria-label="Загрузка правил допуска"
      className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]"
    >
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-10 w-full" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {["a", "b", "c", "d", "e", "f"].map((key) => (
            <Card key={key} className="shadow-none">
              <div className="space-y-3 p-4">
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-3 w-1/2" />
                <Skeleton className="h-3 w-3/5" />
                <Skeleton className="h-3 w-2/5" />
                <Skeleton className="h-3 w-1/3" />
                <div className="flex gap-2 pt-1">
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
            <ShieldCheck className="size-4" aria-hidden="true" />
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-28 w-full" />
        </div>
      </Card>
    </div>
  );
}
