import { Avatar as AvatarPrimitive } from "radix-ui";
import { forwardRef } from "react";
import { cn } from "@/shared/lib/cn";
import type { AvatarProps, AvatarSize } from "./types";

const sizeClasses: Record<AvatarSize, string> = {
  xs: "size-6 text-[0.625rem]",
  sm: "size-8 text-xs",
  md: "size-10 text-sm",
  lg: "size-12 text-base",
  xl: "size-16 text-lg",
};

/**
 * Avatar — a circular user image with graceful initials fallback (Radix
 * Avatar). The fallback surface uses semantic muted tokens, so it themes
 * automatically. When the image errors or is absent, the fallback renders.
 */
export const Avatar = forwardRef<HTMLSpanElement, AvatarProps>(function Avatar(
  { className, src, alt, fallback, size = "md", ...props },
  ref,
) {
  return (
    <AvatarPrimitive.Root
      ref={ref}
      data-slot="avatar"
      className={cn(
        "relative flex shrink-0 select-none overflow-hidden rounded-full",
        sizeClasses[size],
        className,
      )}
      {...props}
    >
      {src != null && (
        <AvatarPrimitive.Image
          src={src}
          alt={alt ?? ""}
          className="aspect-square size-full object-cover"
        />
      )}
      <AvatarPrimitive.Fallback
        // Delay the fallback only when an image may still load, to avoid a flash.
        {...(src != null ? { delayMs: 300 } : {})}
        className="flex size-full items-center justify-center rounded-full bg-muted font-medium text-muted-foreground"
      >
        {fallback}
      </AvatarPrimitive.Fallback>
    </AvatarPrimitive.Root>
  );
});
