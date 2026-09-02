import type { Meta, StoryObj } from "@storybook/react-vite";
import { PosterImage } from "./poster-image";

/** A stand-in poster: portrait 3:4, drawn inline so the story needs no network. */
const PORTRAIT =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
      <rect width="600" height="800" fill="#1d4ed8"/>
      <circle cx="300" cy="300" r="180" fill="#f59e0b"/>
      <text x="300" y="700" fill="#ffffff" font-family="sans-serif" font-size="64"
        text-anchor="middle">АФИША</text>
    </svg>`,
  );

const LANDSCAPE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="500" viewBox="0 0 1600 500">
      <rect width="1600" height="500" fill="#0f766e"/>
      <text x="800" y="290" fill="#ffffff" font-family="sans-serif" font-size="96"
        text-anchor="middle">БАННЕР</text>
    </svg>`,
  );

const meta = {
  title: "Shared/UI/PosterImage",
  component: PosterImage,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
} satisfies Meta<typeof PosterImage>;

export default meta;

type Story = StoryObj<typeof meta>;

/** The case this exists for: a portrait poster in a landscape card frame. */
export const PortraitInLandscapeFrame: Story = {
  args: { src: PORTRAIT, alt: "Афиша фестиваля" },
  render: (args) => (
    <div className="w-72 overflow-hidden rounded-xl border bg-card">
      <div className="aspect-[16/10] bg-muted">
        <PosterImage {...args} />
      </div>
      <p className="p-3 font-semibold text-sm">Фестиваль «Взлёт талантов»</p>
    </div>
  ),
};

/** A wide image in the same frame fills it edge to edge — no bands to blur. */
export const LandscapeInLandscapeFrame: Story = {
  args: { src: LANDSCAPE, alt: "Баннер фестиваля" },
  render: (args) => (
    <div className="w-72 overflow-hidden rounded-xl border bg-card">
      <div className="aspect-[16/10] bg-muted">
        <PosterImage {...args} />
      </div>
      <p className="p-3 font-semibold text-sm">Фестиваль «Взлёт талантов»</p>
    </div>
  ),
};

/** Overlays are siblings after the image, so they stay on top of both layers. */
export const WithOverlay: Story = {
  args: { src: PORTRAIT, alt: "Афиша фестиваля" },
  render: (args) => (
    <div className="relative aspect-[16/10] w-72 overflow-hidden rounded-xl bg-muted">
      <PosterImage {...args} />
      <span className="absolute top-3 left-3 rounded-full bg-background/90 px-2.5 py-1 text-xs font-semibold backdrop-blur">
        Приём заявок
      </span>
    </div>
  ),
};
