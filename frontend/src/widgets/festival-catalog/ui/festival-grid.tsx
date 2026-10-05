import type { Festival } from "@/features/festival-catalog";
import { FestivalCard } from "./festival-card";
import { FestivalCardSkeleton } from "./festival-card-skeleton";

// Two columns from `md`, as the frame has it, and never three: the card carries
// a 406px poster and two full-width actions, and at a third of a page neither
// survives. The gaps are the frame's: 18px between columns, 20px between rows on
// a desktop and 30 on a phone, where one column of cards needs more air to stop
// reading as a single long block.
const GRID_CLASS = "grid grid-cols-1 gap-x-[18px] gap-y-[30px] md:grid-cols-2 xl:gap-y-5";

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
