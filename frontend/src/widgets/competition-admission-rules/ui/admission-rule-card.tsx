import { ArrowDown, Copy, Pencil, Trash2 } from "lucide-react";
import type { AdmissionRuleLabels } from "@/features/competitions/lib/admission-rules";
import type { _AdmissionRule } from "@/shared/api/generated/model-competitions";
import { cn } from "@/shared/lib";
import { Badge, IconButton } from "@/shared/ui";

const CHAIN_KEYS = ["nomination", "discipline", "age", "group", "format"] as const;

interface AdmissionRuleCardProps {
  rule: _AdmissionRule;
  labels: AdmissionRuleLabels;
  readOnly?: boolean;
  onEdit: (rule: _AdmissionRule) => void;
  onDuplicate: (rule: _AdmissionRule) => void;
  onDelete: (rule: _AdmissionRule) => void;
}

export function AdmissionRuleCard({
  rule,
  labels,
  readOnly = false,
  onEdit,
  onDuplicate,
  onDelete,
}: AdmissionRuleCardProps): React.JSX.Element {
  const chain = [
    labels.categoryName,
    labels.disciplineName,
    labels.ageCategoryName,
    labels.participantGroupName,
    labels.participationFormatName,
  ];

  return (
    <li
      className={cn(
        "rounded-lg border border-border bg-card p-3 transition-[opacity,transform] duration-200",
        "[content-visibility:auto] [contain-intrinsic-size:auto_11rem]",
      )}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <Badge variant="success" size="sm">
          Разрешено
        </Badge>
      </div>

      <ol className="space-y-1.5" aria-label="Комбинация правила допуска">
        {chain.map((label, index) => (
          <li key={CHAIN_KEYS[index] ?? label} className="min-w-0">
            {index > 0 ? (
              <ArrowDown className="mb-1 size-3 text-muted-foreground/70" aria-hidden="true" />
            ) : null}
            <p className="truncate font-medium text-sm leading-snug">{label}</p>
          </li>
        ))}
      </ol>

      {!readOnly ? (
        <div className="mt-3 flex items-center gap-1">
          <IconButton
            type="button"
            size="sm"
            variant="ghost"
            aria-label="Редактировать правило допуска"
            icon={<Pencil className="size-3" aria-hidden="true" />}
            onClick={() => onEdit(rule)}
          />
          <IconButton
            type="button"
            size="sm"
            variant="ghost"
            aria-label="Дублировать правило допуска"
            icon={<Copy className="size-3" aria-hidden="true" />}
            onClick={() => onDuplicate(rule)}
          />
          <IconButton
            type="button"
            size="sm"
            variant="ghost"
            aria-label="Удалить правило допуска"
            icon={<Trash2 className="size-3" aria-hidden="true" />}
            onClick={() => onDelete(rule)}
          />
        </div>
      ) : null}
    </li>
  );
}
