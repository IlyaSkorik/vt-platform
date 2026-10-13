import { Skeleton } from "@/shared/ui";

/**
 * Loading placeholder, shaped like the page it stands in for: the banner, then
 * the summary card beside the registration column. Mirroring the real layout is
 * the point — a skeleton of the *old* layout is a worse placeholder than none,
 * because the page visibly jumps when the read lands.
 */
export function LandingSkeleton(): React.JSX.Element {
  return (
    <div aria-hidden="true">
      <Skeleton variant="rect" className="h-[189px] w-full rounded-brand md:h-[343px]" />
      <div className="mt-6 grid items-start gap-6 md:mt-9 lg:grid-cols-[506px_minmax(0,1fr)] lg:gap-[27px]">
        <div className="space-y-2.5">
          <Skeleton variant="rect" className="h-[363px] w-full rounded-brand" />
          <Skeleton variant="rect" className="h-[37px] w-full rounded-brand md:h-[61px]" />
        </div>
        <div className="min-w-0 space-y-4">
          <Skeleton variant="text" className="h-11 w-56" />
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} variant="rect" className="h-[100px] w-full rounded-[19px]" />
          ))}
        </div>
      </div>
    </div>
  );
}
