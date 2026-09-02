import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PosterImage } from "./poster-image";

describe("PosterImage", () => {
  it("shows the whole image and hides the blurred backdrop from assistive tech", () => {
    render(<PosterImage src="/media/poster.png" alt="Афиша фестиваля" />);

    const visible = screen.getByAltText("Афиша фестиваля");
    expect(visible).toHaveClass("object-contain");

    // Both layers are the same file — one request, two roles.
    const backdrop = document.querySelector("img[aria-hidden='true']");
    expect(backdrop).toHaveAttribute("src", "/media/poster.png");
    expect(backdrop).toHaveClass("object-cover", "blur-xl");
  });

  it("leaves a poster without a description decorative", () => {
    const { container } = render(<PosterImage src="/media/poster.png" />);
    const images = container.querySelectorAll("img");
    expect(images).toHaveLength(2);
    for (const image of images) {
      expect(image).toHaveAttribute("alt", "");
    }
  });

  it("puts caller classes on the frame and on the visible image separately", () => {
    render(
      <PosterImage
        src="/media/poster.png"
        alt="Афиша"
        className="rounded-t-xl"
        imageClassName="group-hover:scale-105"
        loading="lazy"
      />,
    );

    expect(screen.getByAltText("Афиша")).toHaveClass("group-hover:scale-105");
    expect(screen.getByAltText("Афиша")).toHaveAttribute("loading", "lazy");
    expect(document.querySelector("[data-slot='poster-image']")).toHaveClass("rounded-t-xl");
  });
});
