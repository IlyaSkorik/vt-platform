import { Card, CardContent, Skeleton } from "@/shared/ui";

/** Loading placeholder mirroring the landing layout (hero + content + sidebar). */
export function LandingSkeleton(): React.JSX.Element {
  return (
    <div className="space-y-8" aria-hidden="true">
      <Skeleton variant="rect" className="h-[22rem] w-full rounded-2xl sm:h-[28rem]" />
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-6 lg:order-1">
          <Skeleton variant="text" className="h-8 w-1/3" />
          <div className="space-y-3">
            <Skeleton variant="text" className="w-full" />
            <Skeleton variant="text" className="w-11/12" />
            <Skeleton variant="text" className="w-4/5" />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((index) => (
              <Skeleton key={index} variant="rect" className="h-28 rounded-lg" />
            ))}
          </div>
        </div>
        <div className="lg:order-2">
          <Card>
            <CardContent className="space-y-4 py-6">
              {[0, 1, 2, 3].map((index) => (
                <Skeleton key={index} variant="text" className="w-full" />
              ))}
              <Skeleton variant="rect" className="h-10 w-full rounded-md" />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
