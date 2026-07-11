const API_PREFIX = "/api/v1";

interface OpenApiLike {
  paths?: Record<string, unknown>;
  servers?: Array<{ url: string; description?: string }>;
  [key: string]: unknown;
}

/**
 * Spectacular emits absolute paths (`/api/v1/competitions/...`), but the SPA
 * already sets `VITE_API_BASE_URL` to `…/api/v1`. Strip the version prefix so
 * Orval matches the Identity contract style (`/competitions`, `/auth/...`).
 */
export default function stripApiVersionPrefix<T extends OpenApiLike>(spec: T): T {
  const nextPaths: Record<string, unknown> = {};

  for (const [path, item] of Object.entries(spec.paths ?? {})) {
    const normalized = path.startsWith(API_PREFIX) ? path.slice(API_PREFIX.length) || "/" : path;
    nextPaths[normalized] = item;
  }

  return {
    ...spec,
    servers: [{ url: API_PREFIX, description: "Versioned API base (API-000 §2)." }],
    paths: nextPaths,
  };
}
