import { Eye, EyeOff } from "lucide-react";
import { forwardRef, useState } from "react";
import { Input } from "@/shared/ui/input";
import type { PasswordInputProps } from "./types";

/**
 * PasswordInput — an {@link Input} preconfigured for secrets, with a built-in
 * reveal toggle.
 *
 * The toggle is a real, labelled `<button>` (never a bare icon), so it is
 * keyboard-operable and announced by screen readers. It inherits all field
 * anatomy (label, error, description) from Input (WCAG 2.1 AA).
 */
export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  function PasswordInput(
    { showLabel = "Показать пароль", hideLabel = "Скрыть пароль", disabled, ...props },
    ref,
  ) {
    const [visible, setVisible] = useState(false);

    return (
      <Input
        ref={ref}
        type={visible ? "text" : "password"}
        disabled={disabled}
        autoComplete="current-password"
        action={
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            disabled={disabled}
            aria-label={visible ? hideLabel : showLabel}
            aria-pressed={visible}
            className="flex items-center rounded-sm text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none [&_svg]:size-4"
          >
            {visible ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
          </button>
        }
        {...props}
      />
    );
  },
);
