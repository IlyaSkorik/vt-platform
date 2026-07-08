import type { InputProps } from "@/shared/ui/input";

export interface PasswordInputProps extends Omit<InputProps, "type" | "trailingIcon" | "action"> {
  /** Accessible label for the reveal toggle when the password is hidden. */
  showLabel?: string;
  /** Accessible label for the reveal toggle when the password is visible. */
  hideLabel?: string;
}
