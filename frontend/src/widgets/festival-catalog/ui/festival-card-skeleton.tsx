import { Card, CardContent, CardFooter, Skeleton } from "@/shared/ui";

/** Placeholder tile matching {@link FestivalCard}'s footprint during loading. */
export function FestivalCardSkeleton(): React.JSX.Element {
  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <Skeleton variant="rect" className="aspect-[16/10] w-full rounded-none" />
      <CardContent className="flex flex-1 flex-col gap-3 pt-5">
        <Skeleton variant="text" className="h-5 w-4/5" />
        <Skeleton variant="text" className="h-4 w-1/2" />
        <div className="space-y-2 pt-1">
          <Skeleton variant="text" className="h-3 w-2/3" />
          <Skeleton variant="text" className="h-3 w-1/2" />
        </div>
        <div className="mt-auto flex gap-1.5 pt-1">
          <Skeleton variant="rect" className="h-5 w-16 rounded-full" />
          <Skeleton variant="rect" className="h-5 w-16 rounded-full" />
        </div>
      </CardContent>
      <CardFooter className="flex items-center justify-between gap-3 border-t pt-4">
        <Skeleton variant="circle" className="size-8" />
        <Skeleton variant="rect" className="h-8 w-28 rounded-md" />
      </CardFooter>
    </Card>
  );
}
