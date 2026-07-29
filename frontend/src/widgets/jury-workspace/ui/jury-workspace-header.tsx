import { Gavel } from "lucide-react";

interface JuryWorkspaceHeaderProps {
  sectionTitle: string;
  sectionDescription: string;
}

export function JuryWorkspaceHeader({
  sectionTitle,
  sectionDescription,
}: JuryWorkspaceHeaderProps): React.JSX.Element {
  return (
    <header className="flex flex-col gap-3 border-border border-b bg-card px-4 py-4 md:px-6">
      <div className="flex items-center gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <Gavel className="size-5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h1 className="truncate font-semibold text-foreground text-lg">Жюри</h1>
          <p className="truncate text-muted-foreground text-sm">
            Рабочее пространство жюри: итоги по номинациям и их публикация.
          </p>
        </div>
      </div>
      <div className="min-w-0">
        <h2 className="font-medium text-foreground text-sm">{sectionTitle}</h2>
        <p className="text-muted-foreground text-sm">{sectionDescription}</p>
      </div>
    </header>
  );
}
