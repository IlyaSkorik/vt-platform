export type AutosaveState = "idle" | "dirty" | "saving" | "saved" | "error";

export const AUTOSAVE_LABELS: Record<AutosaveState, string> = {
  idle: "Все изменения сохранены",
  dirty: "Есть несохранённые изменения",
  saving: "Сохранение…",
  saved: "Сохранено",
  error: "Ошибка сохранения",
};
