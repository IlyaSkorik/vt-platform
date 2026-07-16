import { defineConfig } from "orval";

/**
 * Orval configuration — generates the typed API SDK and TanStack Query hooks
 * from the backend's OpenAPI 3.1 contract (drf-spectacular, ARCH-001 §10.1).
 *
 * Two contracts are generated into the same output tree:
 * - `schema.yaml` — the committed Identity subset consumed by auth UI.
 * - `schema-full.yaml` — the full backend schema; only the Competitions tag is
 *   emitted so organizer endpoints stay typed without breaking Identity names.
 *
 * Regenerate:
 *   1. (backend)  python manage.py spectacular --file ../frontend/openapi/schema-full.yaml
 *   2. (frontend) pnpm api:generate
 */
export default defineConfig({
  vt: {
    input: {
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
  vtCompetitions: {
    input: {
      target: "./openapi/schema-full.yaml",
      // Spectacular paths include `/api/v1`; VITE_API_BASE_URL already has it.
      override: {
        transformer: "./openapi/strip-api-version-prefix.ts",
      },
      filters: {
        tags: ["Competitions"],
      },
    },
    output: {
      mode: "tags-split",
      target: "./src/shared/api/generated",
      schemas: "./src/shared/api/generated/model-competitions",
      client: "fetch",
      httpClient: "fetch",
      clean: false,
      override: {
        mutator: {
          path: "./src/shared/api/orval-mutator.ts",
          name: "customInstance",
        },
        operationName: (operation) => {
          const id = operation.operationId ?? "operation";
          return id.endsWith("Competition") && id.startsWith("create") ? "postCompetition" : id;
        },
      },
    },
  },
  vtApplications: {
    input: {
      target: "./openapi/schema-full.yaml",
      override: {
        transformer: "./openapi/strip-api-version-prefix.ts",
      },
      filters: {
        // The applicant-facing application (order) lifecycle plus its file
        // attachments — the backend the Registration Wizard is a thin client over.
        tags: ["Applications", "Submissions", "Submission Attachments"],
      },
    },
    output: {
      mode: "tags-split",
      target: "./src/shared/api/generated",
      schemas: "./src/shared/api/generated/model-applications",
      client: "react-query",
      httpClient: "fetch",
      clean: false,
      override: {
        mutator: {
          path: "./src/shared/api/orval-mutator.ts",
          name: "customInstance",
        },
        query: {
          useQuery: true,
        },
      },
    },
  },
  vtTeachers: {
    input: {
      target: "./openapi/schema-full.yaml",
      override: {
        transformer: "./openapi/strip-api-version-prefix.ts",
      },
      filters: {
        // The personal, reusable teacher directory owned by the applicant.
        tags: ["Teacher Directory"],
      },
    },
    output: {
      mode: "tags-split",
      target: "./src/shared/api/generated",
      schemas: "./src/shared/api/generated/model-teachers",
      client: "react-query",
      httpClient: "fetch",
      clean: false,
      override: {
        mutator: {
          path: "./src/shared/api/orval-mutator.ts",
          name: "customInstance",
        },
        query: {
          useQuery: true,
        },
      },
    },
  },
  vtPublicCatalog: {
    input: {
      target: "./openapi/schema-full.yaml",
      override: {
        transformer: "./openapi/strip-api-version-prefix.ts",
      },
      filters: {
        // The participant-facing Public Catalog read model — a dedicated,
        // unauthenticated contract kept separate from the organizer tag.
        tags: ["Public Catalog"],
      },
    },
    output: {
      mode: "tags-split",
      target: "./src/shared/api/generated",
      schemas: "./src/shared/api/generated/model-public-catalog",
      client: "fetch",
      httpClient: "fetch",
      clean: false,
      override: {
        mutator: {
          path: "./src/shared/api/orval-mutator.ts",
          name: "customInstance",
        },
      },
    },
  },
});
