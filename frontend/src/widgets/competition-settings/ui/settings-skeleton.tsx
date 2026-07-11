import { Card, CardContent, CardHeader, Skeleton } from "@/shared/ui";

export function SettingsSkeleton(): React.JSX.Element {
  return (
    <div className="space-y-4" role="status" aria-label="Загрузка правил участия">
      {Array.from({ length: 4 }).map((_, i) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: skeleton
        <Card key={i}>
          <CardHeader>
            <Skeleton className="h-5 w-40" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-3/4" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
