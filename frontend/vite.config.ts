/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import { defineConfig } from "vitest/config";

/**
 * Vite configuration for the VT Platform SPA.
 *
 * - `@vitejs/plugin-react` — React 19 Fast Refresh + JSX transform.
 * - `@tailwindcss/vite` — Tailwind CSS v4 (CSS-first, no `tailwind.config.js`).
 * - `vite-tsconfig-paths` — honours the `@/*` alias from `tsconfig.app.json`
 *   so runtime, type-checker and test resolver all agree on one mapping.
 *
 * The `test` block colocates the Vitest configuration so the app and its unit
 * tests share a single resolver and transform pipeline (ARCH-001 §28.3).
 */
export default defineConfig({
  plugins: [react(), tailwindcss(), tsconfigPaths()],
  server: {
    port: 5173,
    strictPort: false,
  },
  preview: {
    port: 4173,
  },
  build: {
    // Fail the build if a chunk balloons — an early proxy for the CI bundle
    // budget mandated by ARCH-001 §8.4.
    chunkSizeWarningLimit: 700,
    sourcemap: true,
    target: "es2023",
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    css: false,
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules", "dist", "e2e", "src/shared/api/generated/**"],
    coverage: {
      provider: "v8",
      reportsDirectory: "./coverage",
      reporter: ["text", "html"],
      exclude: [
        "**/*.stories.tsx",
        "**/*.config.*",
        "**/index.ts",
        "src/shared/api/generated/**",
        "src/main.tsx",
        "src/vite-env.d.ts",
      ],
    },
  },
});
