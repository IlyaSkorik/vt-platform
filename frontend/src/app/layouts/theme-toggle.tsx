import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/app/providers";
import { Button } from "@/shared/ui";

/**
 * App-shell control that toggles between light and dark themes.
 * Accessible: labelled for screen readers, reflects state via `aria-pressed`.
 */
export function ThemeToggle(): React.JSX.Element {
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
    >
      {isDark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
    </Button>
  );
}
