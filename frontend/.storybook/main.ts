import type { StorybookConfig } from "@storybook/react-vite";

/**
 * Storybook 9 configuration.
 *
 * Uses the React + Vite builder, which reuses the project's `vite.config.ts`
 * (Tailwind v4, the `@/*` alias) so components render exactly as they do in the
 * app. Docs (autodocs) and accessibility checks are enabled as first-class
 * acceptance criteria for the design system (ARCH-001 §8.3, WCAG 2.1 AA).
 */
const config: StorybookConfig = {
  stories: ["../src/**/*.mdx", "../src/**/*.stories.@(ts|tsx)"],
  addons: ["@storybook/addon-a11y", "@storybook/addon-docs"],
  framework: {
    name: "@storybook/react-vite",
    options: {},
  },
  staticDirs: ["../public"],
  typescript: {
    reactDocgen: "react-docgen-typescript",
  },
};

export default config;
