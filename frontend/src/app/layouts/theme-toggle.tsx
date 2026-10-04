import { useTheme } from "@/app/providers";
import { Button, MoonIcon, SunIcon } from "@/shared/ui";

interface ThemeToggleProps {
  /**
   * Sizing/appearance override for the button. The app shells take the default
   * `md` square; the public header sets it larger, because the Figma bar carries
   * these two icons as the only thing on its right and sizes them to the mark.
   */
  className?: string;
}

/**
 * App-shell control that toggles between light and dark themes.
 * Accessible: labelled for screen readers, reflects state via `aria-pressed`.
 */
export function ThemeToggle({ className }: ThemeToggleProps = {}): React.JSX.Element {
  const { resolvedTheme, toggleTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <Button
      variant="ghost"
      iconOnly
      onClick={toggleTheme}
      aria-pressed={isDark}
      aria-label={isDark ? "Включить светлую тему" : "Включить тёмную тему"}
      title={isDark ? "Светлая тема" : "Тёмная тема"}
      className={className}
    >
      {/* Both faces are the frame's own glyphs — the moon from the day plate,
          the sun from the night one. */}
      {isDark ? <SunIcon aria-hidden="true" /> : <MoonIcon aria-hidden="true" />}
    </Button>
  );
}
