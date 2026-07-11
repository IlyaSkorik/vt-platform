import { Skeleton } from "@/shared/ui";

export function CompetitionsListSkeleton(): React.JSX.Element {
  return (
    <div role="status" aria-label="Загрузка фестивалей" className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Skeleton className="h-9 w-full max-w-sm" />
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-9 w-36" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {["a", "b", "c", "d", "e", "f"].map((key) => (
          <Skeleton key={key} className="h-56 w-full rounded-lg" />
        ))}
      </div>
    </div>
  );
}
