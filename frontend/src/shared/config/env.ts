import { z } from "zod";

/**
 * Typed, validated access to build-time environment variables.
 *
 * Vite exposes only `VITE_`-prefixed variables to the client. We validate them
 * once at module load so a misconfigured deployment fails fast and loudly
 * rather than surfacing as obscure runtime errors deep in the app.
 */
const envSchema = z.object({
  VITE_API_BASE_URL: z.url().default("http://localhost:8000/api/v1"),
  VITE_API_TIMEOUT: z.coerce.number().int().positive().default(15_000),
  VITE_APP_ENV: z.enum(["development", "stage", "production"]).default("development"),
});

const parsed = envSchema.safeParse(import.meta.env);

if (!parsed.success) {
  // Surface every offending variable together; do not boot in a broken state.
  const issues = z.prettifyError(parsed.error);
  throw new Error(`Invalid environment configuration:\n${issues}`);
}

/** Validated, immutable application environment. */
export const env = Object.freeze({
  apiBaseUrl: parsed.data.VITE_API_BASE_URL,
  apiTimeout: parsed.data.VITE_API_TIMEOUT,
  appEnv: parsed.data.VITE_APP_ENV,
  isProduction: parsed.data.VITE_APP_ENV === "production",
  isDev: import.meta.env.DEV,
});

export type Env = typeof env;
