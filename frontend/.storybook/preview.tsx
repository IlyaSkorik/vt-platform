import type { Preview } from "@storybook/react-vite";
import { useEffect } from "react";
import "../src/shared/styles/global.css";

/**
 * Global Storybook preview configuration.
 *
 * - Imports the design-system stylesheet so tokens/utilities are available.
 * - Adds a theme toolbar that toggles the `.dark` class, mirroring the app's
 *   class-based dark mode, so every story is reviewable in both themes.
 */
const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    layout: "centered",
  },
  globalTypes: {
    theme: {
      description: "Colour theme",
      defaultValue: "light",
      toolbar: {
        title: "Theme",
        icon: "circlehollow",
        items: [
          { value: "light", title: "Светлая" },
          { value: "dark", title: "Тёмная" },
        ],
        dynamicTitle: true,
      },
    },
  },
  decorators: [
    (Story, context) => {
      const theme = context.globals.theme as "light" | "dark";
      useEffect(() => {
        document.documentElement.classList.toggle("dark", theme === "dark");
      }, [theme]);
      return <Story />;
    },
  ],
};

export default preview;
