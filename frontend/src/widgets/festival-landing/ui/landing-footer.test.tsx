import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeContacts, makeSupporter } from "@/features/festival-landing/lib/fixtures";
import { LandingFooter } from "./landing-footer";

describe("LandingFooter", () => {
  it("names the supporting entity beside the organizer, each with its own channels", () => {
    render(
      <LandingFooter
        contacts={makeContacts({
          organizationName: "ООО «Мелодия»",
          phone: "+375 29 111-11-11",
          supporter: makeSupporter({
            name: "ГУ «Дворец культуры»",
            phone: "+375 17 222-22-22",
          }),
        })}
      />,
    );

    expect(screen.getByText("ООО «Мелодия»")).toBeInTheDocument();
    expect(screen.getByText("При поддержке")).toBeInTheDocument();
    expect(screen.getByText("ГУ «Дворец культуры»")).toBeInTheDocument();
    // Both numbers are on the page, each in its own column — the supporting entity's
    // phone landing in the organizer's list would state something untrue.
    expect(screen.getByText("+375 29 111-11-11")).toBeInTheDocument();
    expect(screen.getByText("+375 17 222-22-22")).toBeInTheDocument();
  });

  it("labels the organizer only once there is a second entity to tell it from", () => {
    const { rerender } = render(<LandingFooter contacts={makeContacts({ supporter: null })} />);
    expect(screen.queryByText("Организатор")).not.toBeInTheDocument();

    rerender(<LandingFooter contacts={makeContacts({ supporter: makeSupporter() })} />);
    expect(screen.getByText("Организатор")).toBeInTheDocument();
  });

  it("renders no supporting block at all when the festival has none", () => {
    render(<LandingFooter contacts={makeContacts({ supporter: null })} />);
    expect(screen.queryByText("При поддержке")).not.toBeInTheDocument();
  });

  it("attributes each set of requisites to its own entity", () => {
    render(
      <LandingFooter
        contacts={makeContacts({
          legalInformation: "ООО «Мелодия», УНП 191234567",
          supporter: makeSupporter({ legalInformation: "ГУ «Дворец культуры», УНП 100987654" }),
        })}
      />,
    );

    expect(screen.getByText("ООО «Мелодия», УНП 191234567")).toBeInTheDocument();
    // Prefixed: two УНП lines in a row otherwise read as one entity's, and whose
    // number it is happens to be the entire reason the block exists.
    expect(
      screen.getByText(/При поддержке: ГУ «Дворец культуры», УНП 100987654/),
    ).toBeInTheDocument();
  });
});
