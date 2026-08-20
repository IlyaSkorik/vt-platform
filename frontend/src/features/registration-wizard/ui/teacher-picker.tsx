import { UserPlus } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router";

import { type DirectoryTeacher, useTeachers } from "@/entities/teacher";
import { ROUTES } from "@/shared/config";
import {
  Avatar,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  EmptyState,
  Input,
  LoadingState,
} from "@/shared/ui";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part[0]?.toUpperCase() ?? "").join("") || "?";
}

/**
 * A searchable picker over the user's Personal Teacher Directory, used by the
 * wizard to credit an existing teacher on a performance. It never asks for teacher
 * details — those belong to the directory. Creating a new teacher reuses the
 * existing Teacher Directory page and returns to the wizard.
 */
export function TeacherPicker({
  open,
  onOpenChange,
  onSelect,
  submissionId,
  returnTo,
  isCrediting,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (teacher: DirectoryTeacher) => void;
  submissionId: string;
  returnTo: string;
  isCrediting?: boolean;
}): React.JSX.Element {
  const [search, setSearch] = useState("");
  const { data: teachers, isLoading } = useTeachers();
  const navigate = useNavigate();

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    const list = teachers ?? [];
    if (!query) {
      return list;
    }
    return list.filter((teacher) =>
      `${teacher.displayName} ${teacher.role}`.toLowerCase().includes(query),
    );
  }, [teachers, search]);

  const goCreate = () => {
    const params = new URLSearchParams({ returnTo, submissionId });
    navigate(`${ROUTES.cabinetTeacherNew}?${params.toString()}`);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle>Выберите педагога</DialogTitle>
          <DialogDescription>
            Педагоги берутся из вашего справочника — данные вводить повторно не нужно.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <Input
            leadingIcon={<UserPlus className="size-4" />}
            placeholder="Поиск педагогов"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />

          <div className="flex max-h-80 flex-col gap-2 overflow-y-auto">
            {isLoading ? (
              <LoadingState label="Загружаем справочник…" size="sm" />
            ) : filtered.length === 0 ? (
              <EmptyState
                title={search ? "Ничего не найдено" : "В справочнике пока нет педагогов"}
                description={
                  search
                    ? "Измените запрос или создайте нового педагога."
                    : "Создайте первого педагога — он останется в справочнике."
                }
              />
            ) : (
              filtered.map((teacher) => (
                <div
                  key={teacher.id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-border p-3"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <Avatar alt={teacher.displayName} fallback={initials(teacher.displayName)} />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{teacher.displayName}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {teacher.role}
                        {teacher.email ? ` · ${teacher.email}` : ""}
                      </p>
                    </div>
                  </div>
                  <Button
                    size="xs"
                    disabled={isCrediting ?? false}
                    onClick={() => onSelect(teacher)}
                  >
                    Выбрать
                  </Button>
                </div>
              ))
            )}
          </div>

          <div>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<UserPlus className="size-4" />}
              onClick={goCreate}
            >
              Создать педагога
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
