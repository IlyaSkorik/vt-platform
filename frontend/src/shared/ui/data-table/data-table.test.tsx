import type { ColumnDef } from "@tanstack/react-table";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createRef } from "react";
import { describe, expect, it } from "vitest";
import { DataTable } from "./data-table";

interface Person {
  id: number;
  name: string;
  age: number;
}

const data: Person[] = [
  { id: 1, name: "Борис", age: 30 },
  { id: 2, name: "Анна", age: 25 },
  { id: 3, name: "Виктор", age: 40 },
];

const columns: ColumnDef<Person, unknown>[] = [
  { accessorKey: "name", header: "Имя" },
  { accessorKey: "age", header: "Возраст" },
];

function bodyNames(): string[] {
  const rows = within(screen.getByRole("table")).getAllByRole("row");
  // First row is the header.
  return rows.slice(1).map((row) => within(row).getAllByRole("cell")[0]?.textContent ?? "");
}

describe("DataTable", () => {
  it("renders headers and cells", () => {
    render(<DataTable columns={columns} data={data} />);
    expect(screen.getByRole("columnheader", { name: /Имя/ })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: /Возраст/ })).toBeInTheDocument();
    expect(screen.getByText("Борис")).toBeInTheDocument();
    expect(screen.getByText("Анна")).toBeInTheDocument();
  });

  it("sorts rows when a sortable header is clicked", async () => {
    const user = userEvent.setup();
    render(<DataTable columns={columns} data={data} />);
    expect(bodyNames()).toEqual(["Борис", "Анна", "Виктор"]);
    await user.click(screen.getByRole("button", { name: /Имя/ }));
    expect(bodyNames()).toEqual(["Анна", "Борис", "Виктор"]);
  });

  it("exposes aria-sort on the active column after sorting", async () => {
    const user = userEvent.setup();
    render(<DataTable columns={columns} data={data} />);
    await user.click(screen.getByRole("button", { name: /Имя/ }));
    expect(screen.getByRole("columnheader", { name: /Имя/ })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );
  });

  it("does not render sort buttons when sorting is disabled", () => {
    render(<DataTable columns={columns} data={data} enableSorting={false} />);
    expect(screen.queryByRole("button", { name: /Имя/ })).not.toBeInTheDocument();
  });

  it("shows a loading indicator when loading", () => {
    render(<DataTable columns={columns} data={[]} loading />);
    expect(screen.getByRole("status", { name: "Загрузка" })).toBeInTheDocument();
  });

  it("renders default empty content when there are no rows", () => {
    render(<DataTable columns={columns} data={[]} />);
    expect(screen.getByText("Нет данных")).toBeInTheDocument();
  });

  it("renders custom empty content", () => {
    render(<DataTable columns={columns} data={[]} emptyContent={<span>Ничего не найдено</span>} />);
    expect(screen.getByText("Ничего не найдено")).toBeInTheDocument();
  });

  it("forwards a ref to the table element", () => {
    const ref = createRef<HTMLTableElement>();
    render(<DataTable ref={ref} columns={columns} data={data} />);
    expect(ref.current).toBeInstanceOf(HTMLTableElement);
  });
});
