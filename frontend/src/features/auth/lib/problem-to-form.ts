import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { ApiError } from "@/shared/api";

/**
 * Bridge RFC 9457 Problem Details (API-000 §8) into form state.
 *
 * The server returns field-level failures as `errors[]` entries with a JSON
 * Pointer (`/password`) and a `code`/`detail`. We translate the pointer to a
 * React Hook Form field path and call `setError`, so a server-side rejection
 * (e.g. breached password, `422`) lands under the right field — never as a raw
 * server string. Errors that map to no known field become the form-level
 * message the caller renders in an Alert.
 */

/** Map a JSON Pointer (`/password`) to a form field name (`password`). */
function pointerToField(pointer: string | undefined): string | null {
  if (!pointer) {
    return null;
  }
  const segment = pointer.replace(/^\//, "").split("/")[0];
  return segment && segment.length > 0 ? segment : null;
}

interface ApplyOptions<TValues extends FieldValues> {
  /** RHF `setError`. */
  setError: UseFormSetError<TValues>;
  /** Field names the form actually owns; unmapped errors bubble to form level. */
  knownFields: ReadonlyArray<Path<TValues>>;
}

/**
 * Apply an {@link ApiError}'s field errors to a form and return a human message
 * suitable for a form-level Alert (or `null` when every error was field-mapped).
 */
export function applyProblemToForm<TValues extends FieldValues>(
  error: unknown,
  { setError, knownFields }: ApplyOptions<TValues>,
): string | null {
  if (!(error instanceof ApiError)) {
    return "Произошла непредвиденная ошибка. Повторите попытку.";
  }

  const known = new Set<string>(knownFields as readonly string[]);
  let mappedCount = 0;

  for (const fieldError of error.fieldErrors) {
    const field = pointerToField(fieldError.pointer);
    const detail = fieldError.detail ?? "Некорректное значение";
    if (field && known.has(field)) {
      setError(field as Path<TValues>, { type: "server", message: detail });
      mappedCount += 1;
    }
  }

  if (mappedCount > 0 && mappedCount === error.fieldErrors.length) {
    return null;
  }

  return formLevelMessage(error);
}

/** A safe, human-readable message for a form-level Alert (never a raw trace). */
export function formLevelMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "Произошла непредвиденная ошибка. Повторите попытку.";
  }
  if (error.status === 0) {
    return "Не удалось связаться с сервером. Проверьте подключение к сети.";
  }
  if (error.status === 429) {
    return "Слишком много попыток. Пожалуйста, повторите позже.";
  }
  return error.problem?.detail ?? error.problem?.title ?? error.message;
}
