import { useState } from "react";

import {
  MODULE_LABELS,
  MODULE_PRESETS,
  PLATFORM_MODULES,
  type PlatformModule,
  refusalMessage,
  useOrganizationModules,
  useSetOrganizationModules,
} from "@/applications/platform/api/platform-api";
import { Button, LoadingState, Switch, toast } from "@/shared/ui";

/** Same set, order-insensitive — whether the form still says what the server holds. */
function sameSet(left: PlatformModule[], right: PlatformModule[]): boolean {
  if (left.length !== right.length) {
    return false;
  }
  const held = new Set(right);
  return left.every((module) => held.has(module));
}

/**
 * Which parts of the platform one organization was sold.
 *
 * Draft-then-save rather than a switch that writes on every click: turning six
 * modules off one at a time would be six writes, six invalidations, and six
 * moments where the organizer's panel is in a state nobody intended. The operator
 * arranges the board, then commits it.
 *
 * The presets are buttons that fill the draft, not a separate thing to save. That
 * keeps "only the audience vote" a shortcut rather than a mode, and lets the
 * operator adjust one switch afterwards without leaving the preset behind.
 */
export function ModuleSwitchboard({
  organizationId,
}: {
  organizationId: string;
}): React.JSX.Element {
  const modules = useOrganizationModules(organizationId);
  const save = useSetOrganizationModules();
  const [draft, setDraft] = useState<PlatformModule[] | null>(null);

  const held = (modules.data?.modules ?? []).filter((row) => row.enabled).map((row) => row.module);
  // Null draft means "nothing touched yet", so the board shows what the server
  // holds. Once the operator moves a switch their arrangement wins until they
  // save it — a refetch landing mid-edit must not quietly discard their work.
  // The save clears the draft, and the refreshed query becomes the truth again.
  const current = draft ?? held;

  if (modules.isLoading) {
    return <LoadingState label="Загрузка модулей" size="sm" />;
  }

  if (modules.isError) {
    return <p className="text-muted-foreground text-sm">Не удалось загрузить модули.</p>;
  }

  const toggle = (module: PlatformModule, enabled: boolean): void => {
    setDraft(enabled ? [...current, module] : current.filter((candidate) => candidate !== module));
  };

  const commit = (): void => {
    save.mutate(
      { id: organizationId, modules: current },
      {
        onSuccess: () => {
          setDraft(null);
          toast.success("Набор модулей сохранён");
        },
        onError: async (error) => {
          toast.error(await refusalMessage(error, "Не удалось сохранить модули"));
        },
      },
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <p className="font-medium text-sm">Подключённые модули</p>
        <p className="text-muted-foreground text-xs">
          Организация видит только то, что здесь включено. Профиль, сотрудники и настройки доступны
          всегда.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {/* Outlined, not ghost. A ghost button is text until you hover it, and on a
            touch screen there is no hovering — these read as a sentence somebody
            forgot to format rather than as the three shortcuts they are. */}
        {MODULE_PRESETS.map((preset) => (
          <Button
            key={preset.id}
            size="sm"
            variant="outline"
            onClick={() => setDraft([...preset.modules])}
          >
            {preset.label}
          </Button>
        ))}
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {PLATFORM_MODULES.map((module) => (
          <Switch
            key={module}
            size="sm"
            label={MODULE_LABELS[module]}
            checked={current.includes(module)}
            onCheckedChange={(checked) => toggle(module, checked)}
          />
        ))}
      </div>

      <div>
        <Button
          variant="outline"
          loading={save.isPending}
          disabled={sameSet(current, held)}
          onClick={commit}
        >
          Сохранить модули
        </Button>
      </div>
    </div>
  );
}
