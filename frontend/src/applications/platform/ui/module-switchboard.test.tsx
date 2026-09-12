import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const save = vi.fn();
let modules: { isLoading: boolean; isError: boolean; data?: unknown };

vi.mock("@/applications/platform/api/platform-api", async () => {
  const PLATFORM_MODULES = ["COMPETITIONS", "DIPLOMAS", "VOTING"];
  return {
    PLATFORM_MODULES,
    MODULE_LABELS: {
      COMPETITIONS: "Фестивали",
      DIPLOMAS: "Дипломы",
      VOTING: "Зрительское голосование",
    },
    MODULE_PRESETS: [
      { id: "full", label: "Полный доступ", modules: PLATFORM_MODULES },
      { id: "voting", label: "Только голосование", modules: ["VOTING"] },
    ],
    useOrganizationModules: () => modules,
    useSetOrganizationModules: () => ({ mutate: save, isPending: false }),
    refusalMessage: async (_error: unknown, fallback: string) => fallback,
  };
});

const { ModuleSwitchboard } = await import("./module-switchboard");

function held(...enabled: string[]) {
  return {
    isLoading: false,
    isError: false,
    data: {
      organizationId: "org-1",
      modules: ["COMPETITIONS", "DIPLOMAS", "VOTING"].map((module) => ({
        module,
        enabled: enabled.includes(module),
        enabledAt: null,
        disabledAt: null,
      })),
    },
  };
}

beforeEach(() => {
  save.mockReset();
  modules = held("COMPETITIONS", "DIPLOMAS", "VOTING");
});

describe("the module switchboard", () => {
  it("shows what the organization currently holds", () => {
    modules = held("VOTING");
    render(<ModuleSwitchboard organizationId="org-1" />);

    expect(screen.getByRole("switch", { name: "Зрительское голосование" })).toBeChecked();
    expect(screen.getByRole("switch", { name: "Дипломы" })).not.toBeChecked();
  });

  it("saves nothing until the operator commits the board", async () => {
    render(<ModuleSwitchboard organizationId="org-1" />);

    await userEvent.click(screen.getByRole("switch", { name: "Дипломы" }));

    expect(save).not.toHaveBeenCalled();
  });

  it("commits the whole set in one write", async () => {
    render(<ModuleSwitchboard organizationId="org-1" />);

    await userEvent.click(screen.getByRole("switch", { name: "Дипломы" }));
    await userEvent.click(screen.getByRole("button", { name: "Сохранить модули" }));

    await waitFor(() => expect(save).toHaveBeenCalledTimes(1));
    expect(save.mock.calls[0]?.[0].modules.toSorted()).toEqual(["COMPETITIONS", "VOTING"]);
  });

  it("a preset fills the board without saving it", async () => {
    render(<ModuleSwitchboard organizationId="org-1" />);

    await userEvent.click(screen.getByRole("button", { name: "Только голосование" }));

    expect(screen.getByRole("switch", { name: "Фестивали" })).not.toBeChecked();
    expect(screen.getByRole("switch", { name: "Зрительское голосование" })).toBeChecked();
    expect(save).not.toHaveBeenCalled();
  });

  it("the save button stays inert while the board says what the server holds", () => {
    render(<ModuleSwitchboard organizationId="org-1" />);

    expect(screen.getByRole("button", { name: "Сохранить модули" })).toBeDisabled();
  });

  it("an empty board is savable — an organization may hold nothing", async () => {
    modules = held("VOTING");
    render(<ModuleSwitchboard organizationId="org-1" />);

    await userEvent.click(screen.getByRole("switch", { name: "Зрительское голосование" }));
    await userEvent.click(screen.getByRole("button", { name: "Сохранить модули" }));

    await waitFor(() => expect(save).toHaveBeenCalledTimes(1));
    expect(save.mock.calls[0]?.[0].modules).toEqual([]);
  });
});
