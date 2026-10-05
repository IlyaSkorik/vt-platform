/**
 * The Performance Builder, and the one rule that removes a control from it.
 *
 * A festival that judges one act per entrant turns `allowMultiplePerformances` off,
 * and the Applications context then refuses a second performance on the endpoint.
 * What this suite pins down is that the button is *absent* rather than present and
 * rejected — a visible control that always fails is the failure mode worth a test —
 * and that it comes back when the order is empty, because removing the one
 * performance has to leave a way to enter another.
 */
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApplicationResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";

import { PerformanceBuilder } from "./performance-builder";

const addSubmission = vi.fn();
const removeSubmission = vi.fn();
const duplicate = vi.fn();

vi.mock("@/entities/application", () => ({
  useAddSubmission: () => ({ mutate: addSubmission, isPending: false }),
  useRemoveSubmission: () => ({ mutate: removeSubmission, isPending: false }),
}));

vi.mock("../api/duplicate", () => ({
  useDuplicatePerformance: () => ({ mutate: duplicate, isPending: false }),
}));

// The card owns its own data access and its own form; this suite is about which
// controls the builder offers, so it is reduced to the two buttons that matter.
vi.mock("./performance-card", () => ({
  PerformanceCard: ({
    onDuplicate,
    onRemove,
  }: {
    onDuplicate: (() => void) | null;
    onRemove: (() => void) | null;
  }) => (
    <div>
      {onDuplicate ? <button type="button">Дублировать</button> : null}
      {onRemove ? <button type="button">Удалить</button> : null}
    </div>
  ),
}));

const APPLICATION_ID = "01900000-0000-7000-8000-000000000001";

function registration(allowMultiplePerformances: boolean): Registration {
  return { allowMultiplePerformances } as Registration;
}

function application(count: number): ApplicationResource {
  return {
    submissions: Array.from({ length: count }, (_, index) => ({
      submissionId: `01900000-0000-7000-8000-00000000000${index + 1}`,
    })),
  } as ApplicationResource;
}

function renderBuilder(count: number, allowMultiple: boolean, composable = true): void {
  render(
    <PerformanceBuilder
      applicationId={APPLICATION_ID}
      application={application(count)}
      registration={registration(allowMultiple)}
      composable={composable}
    />,
  );
}

const ADD = /Добавить выступление/;

describe("PerformanceBuilder", () => {
  beforeEach(() => {
    addSubmission.mockClear();
    duplicate.mockClear();
  });

  it("offers the add button when the festival takes several performances", () => {
    renderBuilder(1, true);

    expect(screen.getByRole("button", { name: ADD })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Дублировать/ })).toBeInTheDocument();
  });

  it("drops add and duplicate once a one-performance festival has its one", () => {
    renderBuilder(1, false);

    expect(screen.queryByRole("button", { name: ADD })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Дублировать/ })).not.toBeInTheDocument();
    expect(screen.getByText(/принимает одно выступление/)).toBeInTheDocument();
  });

  it("still offers the add button on an empty one-performance order", () => {
    // Otherwise removing the one performance would leave the order unenterable.
    renderBuilder(0, false);

    expect(screen.getByRole("button", { name: ADD })).toBeInTheDocument();
  });

  it("keeps adding available past the first performance when several are allowed", () => {
    renderBuilder(3, true);

    expect(screen.getByRole("button", { name: ADD })).toBeInTheDocument();
  });

  it("drops every composition control on a paid order", () => {
    // Сумма оплаченного заказа заморожена, поэтому всё, что её двигает, не просто
    // откажет на сервере — его здесь нет. Сами выступления остаются открытыми.
    renderBuilder(2, true, false);

    expect(screen.queryByRole("button", { name: ADD })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Дублировать/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Удалить/ })).not.toBeInTheDocument();
  });
});
