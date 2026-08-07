import { LoadingState } from "@/shared/ui";

/**
 * What the app shows while the first route's module is still downloading.
 *
 * Every route in this application is `lazy`, so the very first render always has
 * to wait for a chunk. React Router calls that window "hydration" even with no
 * SSR behind it, and without a fallback it renders nothing and warns — leaving a
 * blank page for however long that chunk takes, which on a cold cache over a
 * phone connection is long enough to read as broken.
 *
 * Full-viewport and centred, because there is no layout yet to sit inside: the
 * layouts are themselves part of the route tree being loaded.
 */
export function RouteHydrateFallback(): React.JSX.Element {
  return (
    <div className="flex min-h-svh items-center justify-center bg-background text-foreground">
      <LoadingState label="Загрузка" size="lg" />
    </div>
  );
}
