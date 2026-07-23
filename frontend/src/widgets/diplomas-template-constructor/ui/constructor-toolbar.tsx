import { ArrowLeft, ChevronRight, Eye, FileUp, Save } from "lucide-react";
import { Link } from "react-router";
import { ROUTES } from "@/shared/config";
import { Button } from "@/shared/ui";

interface ConstructorToolbarProps {
  templateName: string;
  /** Whether a PDF is attached — switches the upload action label. */
  hasDocument: boolean;
  onRequestUpload: () => void;
  isUploading: boolean;
  onSave: () => void;
  isSaving: boolean;
  /** Unsaved changes present — enables the Save button. */
  dirty: boolean;
}

const TEMPLATES_PATH = `${ROUTES.staffDiplomas}?section=templates`;

export function ConstructorToolbar({
  templateName,
  hasDocument,
  onRequestUpload,
  isUploading,
  onSave,
  isSaving,
  dirty,
}: ConstructorToolbarProps): React.JSX.Element {
  return (
    <header className="flex flex-col gap-3 border-border border-b bg-card px-4 py-3 md:flex-row md:items-center md:justify-between md:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <Button asChild variant="ghost" size="sm" iconOnly aria-label="Назад к шаблонам">
          <Link to={TEMPLATES_PATH}>
            <ArrowLeft className="size-4" aria-hidden="true" />
          </Link>
        </Button>
        <div className="min-w-0">
          <nav aria-label="Хлебные крошки">
            <ol className="flex items-center gap-1 text-muted-foreground text-xs">
              <li>
                <Link to={ROUTES.staffDiplomas} className="hover:text-foreground hover:underline">
                  Дипломы
                </Link>
              </li>
              <ChevronRight className="size-3" aria-hidden="true" />
              <li>
                <Link to={TEMPLATES_PATH} className="hover:text-foreground hover:underline">
                  Шаблоны
                </Link>
              </li>
              <ChevronRight className="size-3" aria-hidden="true" />
              <li className="max-w-[12rem] truncate text-foreground">{templateName}</li>
              <ChevronRight className="size-3" aria-hidden="true" />
              <li>Конструктор</li>
            </ol>
          </nav>
          <h1 className="truncate font-semibold text-base text-foreground">{templateName}</h1>
        </div>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={onRequestUpload} disabled={isUploading}>
          <FileUp className="size-4" aria-hidden="true" />
          {isUploading ? "Загрузка…" : hasDocument ? "Заменить PDF" : "Загрузить PDF"}
        </Button>
        {/* Preview lands in a later milestone — present but inert. */}
        <Button variant="outline" size="sm" disabled>
          <Eye className="size-4" aria-hidden="true" />
          Предпросмотр
        </Button>
        <Button size="sm" onClick={onSave} disabled={!dirty || isSaving}>
          <Save className="size-4" aria-hidden="true" />
          {isSaving ? "Сохранение…" : "Сохранить"}
        </Button>
      </div>
    </header>
  );
}
