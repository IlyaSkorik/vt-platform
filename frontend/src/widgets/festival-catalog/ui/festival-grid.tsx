import type { Festival } from "@/features/festival-catalog";
import { FestivalCard } from "./festival-card";
import { FestivalCardSkeleton } from "./festival-card-skeleton";

const GRID_CLASS = "grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3";

interface FestivalGridProps {
  festivals: Festival[];
  now: Date;
}

/** Responsive card grid: 1 column on mobile, 2 on tablet, 3 on desktop. */
export function FestivalGrid({ festivals, now }: FestivalGridProps): React.JSX.Element {
  return (
    <div className={GRID_CLASS}>
      {festivals.map((festival) => (
        <FestivalCard key={festival.id} festival={festival} now={now} />
      ))}
    </div>
  );
}

interface FestivalGridSkeletonProps {
  count?: number;
}

/** Skeleton grid shown while the catalog loads (optimistic layout). */
export function FestivalGridSkeleton({ count = 6 }: FestivalGridSkeletonProps): React.JSX.Element {
  return (
    <div className={GRID_CLASS} aria-hidden="true">
      {Array.from({ length: count }, (_, index) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: fixed-length static placeholder list
        <FestivalCardSkeleton key={index} />
      ))}
    </div>
  );
}
