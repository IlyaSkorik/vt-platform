import { Monitor, Moon, Sun } from "lucide-react";

import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui";

/** The colour-scheme preference, mirroring the app's theme provider. */
export type ThemePreference = "light" | "dark" | "system";

export interface AppearanceCardProps {
  theme: ThemePreference;
  onThemeChange: (theme: ThemePreference) => void;
}

const OPTIONS: { value: ThemePreference; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Светлая", icon: Sun },
  { value: "dark", label: "Тёмная", icon: Moon },
  { value: "system", label: "Как в системе", icon: Monitor },
];

/**
 * The interface's colour scheme.
 *
 * A local preference, not an account setting: it is stored in this browser and
 * never sent anywhere, because "dark on the laptop, light on the tablet" is a
 * perfectly ordinary thing to want and syncing it would take that away. The
 * toggle in the header does the same thing in one click; this is where the third
 * option — follow the operating system — is reachable.
 */
export function AppearanceCard({ theme, onThemeChange }: AppearanceCardProps): React.JSX.Element {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Оформление</CardTitle>
        <CardDescription>
          Тема интерфейса. Сохраняется в этом браузере — на другом устройстве можно выбрать другую.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div role="radiogroup" aria-label="Тема интерфейса" className="flex flex-wrap gap-2">
          {OPTIONS.map(({ value, label, icon: Icon }) => {
            const selected = theme === value;
            return (
              <Button
                key={value}
                type="button"
                role="radio"
                aria-checked={selected}
                variant={selected ? "secondary" : "outline"}
                onClick={() => onThemeChange(value)}
              >
                <Icon className="size-4" aria-hidden="true" />
                {label}
              </Button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
