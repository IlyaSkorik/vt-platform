import type { Festival } from "@/features/festival-catalog";
import { FestivalCard } from "./festival-card";
import { FestivalCardSkeleton } from "./festival-card-skeleton";

// Two columns from `md`, as the frame has it, and never three: the card carries
// a 406px poster and two full-width actions, and at a third of a page neither
// survives. The 18px column gap and 20px row gap are the frame's own.
const GRID_CLASS = "grid grid-cols-1 gap-x-[18px] gap-y-5 md:grid-cols-2";

interface FestivalGridProps {
  festivals: Festival[];
  now: Date;
  detailBasePath: string;
}

/** The catalogue grid: one column on a phone, two from `md`. */
export function FestivalGrid({
  festivals,
  now,
  detailBasePath,
}: FestivalGridProps): React.JSX.Element {
  return (
    <div className={GRID_CLASS}>
      {festivals.map((festival) => (
        <FestivalCard
          key={festival.id}
          festival={festival}
          now={now}
          detailBasePath={detailBasePath}
        />
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
