import { defineConfig } from "orval";

/**
 * Orval configuration — generates the typed API SDK and TanStack Query hooks
 * from the backend's OpenAPI 3.1 contract (drf-spectacular, ARCH-001 §10.1).
 *
 * The SDK is intentionally NOT generated during bootstrap; this file only
 * establishes the contract-to-client pipeline. Once the backend publishes its
 * schema, run:
 *
 *   1. (backend)  python manage.py spectacular --file ../frontend/openapi/schema.yaml
 *   2. (frontend) pnpm api:generate
 *
 * Generation rules:
 * - Output lands in `src/shared/api/generated/` (git-ignored, reproducible).
 * - Every network call routes through our Ky-based `customInstance` mutator,
 *   so auth, retry, timeout and Problem Details mapping stay centralized
 *   (ARCH-001 §8.5 — all calls go through the shared client).
 * - `react-query` client emits colocated hooks that pages/features consume.
 */
export default defineConfig({
  vt: {
    input: {
      // Contract source of truth. Point this at a committed schema file or the
      // live schema endpoint (e.g. http://localhost:8000/api/v1/schema/).
      target: "./openapi/schema.yaml",
    },
    output: {
      mode: "tags-split",
      target: "./src/shared/api/generated",
      schemas: "./src/shared/api/generated/model",
      client: "react-query",
      httpClient: "fetch",
      clean: true,
      override: {
        mutator: {
          path: "./src/shared/api/orval-mutator.ts",
          name: "customInstance",
        },
        query: {
          useQuery: true,
          useInfinite: true,
          useInfiniteQueryParam: "cursor",
        },
      },
    },
  },
});
