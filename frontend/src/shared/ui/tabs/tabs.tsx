import { Tabs as TabsPrimitive } from "radix-ui";
import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import type { TabsContentProps, TabsListProps, TabsProps, TabsTriggerProps } from "./types";

/**
 * Tabs — a set of layered sections wrapping Radix Tabs. Radix supplies roving
 * focus and arrow-key navigation; this layer adds the token-based styling
 * (pill list, active/inactive triggers) so it themes automatically and stays
 * accessible (WCAG 2.1 AA).
 */
export const Tabs = forwardRef<React.ElementRef<typeof TabsPrimitive.Root>, TabsProps>(
  function Tabs({ className, ...props }, ref) {
    return (
      <TabsPrimitive.Root
        ref={ref}
        data-slot="tabs"
        className={cn("flex flex-col gap-2", className)}
        {...props}
      />
    );
  },
);

export const TabsList = forwardRef<React.ElementRef<typeof TabsPrimitive.List>, TabsListProps>(
  function TabsList({ className, ...props }, ref) {
    return (
      <TabsPrimitive.List
        ref={ref}
        data-slot="tabs-list"
        className={cn(
          "inline-flex w-fit items-center justify-center gap-1 rounded-lg bg-muted p-1 text-muted-foreground",
          "data-[orientation=vertical]:flex-col",
          className,
        )}
        {...props}
      />
    );
  },
);

export const TabsTrigger = forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  TabsTriggerProps
>(function TabsTrigger({ className, ...props }, ref) {
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      data-slot="tabs-trigger"
      className={cn(
        "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors outline-none",
        "text-muted-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50",
        "data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-elevation-1",
        "disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
        className,
      )}
      {...props}
    />
  );
});

export const TabsContent = forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  TabsContentProps
>(function TabsContent({ className, ...props }, ref) {
  return (
    <TabsPrimitive.Content
      ref={ref}
      data-slot="tabs-content"
      className={cn("outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50", className)}
      {...props}
    />
  );
});
