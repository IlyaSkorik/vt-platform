import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { TemplateField } from "@/features/diplomas";
import { createField, requiredFieldTypes, withRequiredFields } from "./field-factory";
import { useConstructorFields } from "./use-constructor-fields";

function field(type: Parameters<typeof createField>[0]): TemplateField {
  return createField(type, 1);
}

describe("requiredFieldTypes", () => {
  it("requires the QR block on every kind of diploma", () => {
    // Both are numbered and verifiable, and the block is the only place the number
    // and the verification link are printed.
    expect(requiredFieldTypes("DIPLOMA")).toEqual(["qr_block"]);
    expect(requiredFieldTypes("INDIVIDUAL_DIPLOMA")).toEqual(["qr_block"]);
  });

  it("requires nothing of a thank-you letter", () => {
    // It is not registered at all, and the backend rejects a QR block on one.
    expect(requiredFieldTypes("THANK_YOU")).toEqual([]);
  });

  it("forces nothing onto a kind this build does not know", () => {
    expect(requiredFieldTypes("CERTIFICATE")).toEqual([]);
  });
});

describe("withRequiredFields", () => {
  it("adds the QR block to a diploma layout that has none", () => {
    const saved = [field("participant_name")];

    const completed = withRequiredFields(saved, "DIPLOMA");

    expect(completed.map((item) => item.type)).toEqual(["participant_name", "qr_block"]);
  });

  it("gives a brand-new diploma template its QR block", () => {
    expect(withRequiredFields([], "DIPLOMA").map((item) => item.type)).toEqual(["qr_block"]);
  });

  it("returns the very same array when nothing is missing", () => {
    // Reference equality is what the editor uses to decide it has nothing to save.
    const saved = [field("participant_name"), field("qr_block")];

    expect(withRequiredFields(saved, "DIPLOMA")).toBe(saved);
    expect(withRequiredFields(saved, "THANK_YOU")).toBe(saved);
  });

  it("puts the QR block in the lower-right corner rather than over the name", () => {
    const [qr] = withRequiredFields([], "DIPLOMA");

    expect(qr?.x).toBeGreaterThan(0.5);
    expect(qr?.y).toBeGreaterThan(0.5);
    // Still on the page.
    expect((qr?.x ?? 0) + (qr?.width ?? 0)).toBeLessThanOrEqual(1);
    expect((qr?.y ?? 0) + (qr?.height ?? 0)).toBeLessThanOrEqual(1);
  });
});

describe("useConstructorFields — required elements", () => {
  const options = { requiredTypes: ["qr_block"] as const };

  it("keeps the only QR block on the template", () => {
    const qr = field("qr_block");
    const { result } = renderHook(() => useConstructorFields([field("teacher"), qr], options));

    act(() => result.current.removeField(qr.id));

    expect(result.current.fields.map((item) => item.type)).toContain("qr_block");
    expect(result.current.canRemoveField(qr.id)).toBe(false);
  });

  it("does not mark the layout dirty over a refused removal", () => {
    const qr = field("qr_block");
    const { result } = renderHook(() => useConstructorFields([qr], options));

    act(() => result.current.removeField(qr.id));

    expect(result.current.dirty).toBe(false);
  });

  it("removes a second QR block, since one still remains", () => {
    const first = field("qr_block");
    const second = field("qr_block");
    const { result } = renderHook(() => useConstructorFields([first, second], options));

    expect(result.current.canRemoveField(second.id)).toBe(true);
    act(() => result.current.removeField(second.id));

    expect(result.current.fields).toHaveLength(1);
    expect(result.current.fields[0]?.id).toBe(first.id);
  });

  it("leaves every other element removable", () => {
    const teacher = field("teacher");
    const { result } = renderHook(() =>
      useConstructorFields([teacher, field("qr_block")], options),
    );

    expect(result.current.canRemoveField(teacher.id)).toBe(true);
    act(() => result.current.removeField(teacher.id));

    expect(result.current.fields.map((item) => item.type)).toEqual(["qr_block"]);
  });

  it("removes anything when the document requires nothing", () => {
    const qr = field("qr_block");
    const { result } = renderHook(() => useConstructorFields([qr]));

    act(() => result.current.removeField(qr.id));

    expect(result.current.fields).toHaveLength(0);
  });

  it("starts dirty when the editor had to complete the loaded layout", () => {
    // Otherwise Save stays disabled and the block the editor just added is never stored.
    const { result } = renderHook(() =>
      useConstructorFields(withRequiredFields([], "DIPLOMA"), { ...options, initialDirty: true }),
    );

    expect(result.current.dirty).toBe(true);
  });
});
