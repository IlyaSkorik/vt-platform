import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  EmptyPage,
  PageActions,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageSection,
  PageTitle,
} from ".";

describe("Page primitives", () => {
  it("renders a container with content", () => {
    render(
      <PageContainer>
        <PageContent>содержимое</PageContent>
      </PageContainer>,
    );
    expect(screen.getByText("содержимое")).toBeInTheDocument();
  });

  it("PageTitle renders an h1 by default and h2 when asked", () => {
    const { rerender } = render(<PageTitle>Заголовок</PageTitle>);
    expect(screen.getByRole("heading", { level: 1, name: "Заголовок" })).toBeInTheDocument();

    rerender(<PageTitle as="h2">Заголовок</PageTitle>);
    expect(screen.getByRole("heading", { level: 2, name: "Заголовок" })).toBeInTheDocument();
  });

  it("PageHeader renders its actions slot", () => {
    render(
      <PageHeader actions={<button type="button">Действие</button>}>
        <PageTitle>Страница</PageTitle>
        <PageDescription>Описание</PageDescription>
      </PageHeader>,
    );
    expect(screen.getByRole("button", { name: "Действие" })).toBeInTheDocument();
    expect(screen.getByText("Описание")).toBeInTheDocument();
  });

  it("PageActions groups action controls", () => {
    render(
      <PageActions>
        <button type="button">Одно</button>
        <button type="button">Два</button>
      </PageActions>,
    );
    expect(screen.getAllByRole("button")).toHaveLength(2);
  });

  it("PageSection renders a titled section header", () => {
    render(
      <PageSection title="Раздел" description="Пояснение">
        тело
      </PageSection>,
    );
    expect(screen.getByRole("heading", { level: 2, name: "Раздел" })).toBeInTheDocument();
    expect(screen.getByText("Пояснение")).toBeInTheDocument();
    expect(screen.getByText("тело")).toBeInTheDocument();
  });

  it("PageSection omits the header when no title/description/actions", () => {
    render(<PageSection>только тело</PageSection>);
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    expect(screen.getByText("только тело")).toBeInTheDocument();
  });

  it("EmptyPage exposes a labelled region", () => {
    render(<EmptyPage title="Скоро" description="Раздел в разработке" />);
    const region = screen.getByRole("region", { name: "Скоро" });
    expect(region).toBeInTheDocument();
    expect(screen.getByText("Раздел в разработке")).toBeInTheDocument();
  });

  it("EmptyPage renders its action slot", () => {
    render(<EmptyPage title="Пусто" action={<button type="button">Назад</button>} />);
    expect(screen.getByRole("button", { name: "Назад" })).toBeInTheDocument();
  });
});
