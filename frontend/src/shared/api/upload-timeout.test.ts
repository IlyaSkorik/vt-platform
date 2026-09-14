import { describe, expect, it } from "vitest";

import { API_TIMEOUT_MS, uploadTimeoutMs } from "./config";

/** Тело с файлом заданного размера — как его собирает сгенерированный клиент. */
function multipart(bytes: number): FormData {
  const body = new FormData();
  body.append("attachmentType", "VIDEO");
  body.append("file", new File([new Uint8Array(bytes)], "номер.mp4", { type: "video/mp4" }));
  return body;
}

describe("uploadTimeoutMs", () => {
  it("оставляет обычному запросу общий таймаут", () => {
    expect(uploadTimeoutMs(undefined)).toBe(API_TIMEOUT_MS);
    expect(uploadTimeoutMs(JSON.stringify({ a: 1 }))).toBe(API_TIMEOUT_MS);
  });

  it("даёт видео с телефона больше пятнадцати секунд", () => {
    // Ровно тот случай, из-за которого загрузка обрывалась: 124 МБ с iPhone.
    const timeout = uploadTimeoutMs(multipart(124 * 1024 * 1024));
    expect(timeout).toBeGreaterThan(API_TIMEOUT_MS);
    expect(timeout).toBeGreaterThan(10 * 60_000);
  });

  it("растёт вместе с файлом, но не бесконечно", () => {
    const small = uploadTimeoutMs(multipart(1024));
    const large = uploadTimeoutMs(multipart(50 * 1024 * 1024));
    expect(small).toBe(60_000);
    expect(large).toBeGreaterThan(small);
    // Потолок: дальше это уже не «медленно», а «не доедет».
    expect(uploadTimeoutMs(multipart(100 * 1024 * 1024))).toBe(30 * 60_000);
  });

  it("считает файлы, а не текстовые поля формы", () => {
    const fields = new FormData();
    fields.append("attachmentType", "MUSIC");
    expect(uploadTimeoutMs(fields)).toBe(60_000);
  });
});
