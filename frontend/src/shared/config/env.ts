import { z } from "zod";

/**
 * Typed, validated access to build-time environment variables.
 *
 * In production the frontend and API are served from the same origin through
 * nginx, therefore VITE_API_BASE_URL may be left empty. In that case we use
 * the relative "/api/v1" endpoint.
 */
const envSchema = z.object({
  VITE_API_BASE_URL: z
    .string()
    .default("")
    .transform((v) => v.trim())
    .refine(
      (v) => v === "" || z.url().safeParse(v).success,
      "Must be empty or a valid absolute URL",
    ),

  VITE_API_TIMEOUT: z.coerce.number().int().positive().default(15_000),

  VITE_APP_ENV: z
    .enum(["development", "stage", "production"])
    .default("development"),

  VITE_SITE_URL: z.url().default("https://vzlettalantov.by"),
});

const parsed = envSchema.safeParse(import.meta.env);

if (!parsed.success) {
  throw new Error(
    `Invalid environment configuration:\n${z.prettifyError(parsed.error)}`,
  );
}

/**
 * Empty VITE_API_BASE_URL means "same origin".
 * This keeps production configuration minimal and avoids hardcoding domains.
 */
const apiBaseUrl =
  parsed.data.VITE_API_BASE_URL === ""
    ? "/api/v1"
    : parsed.data.VITE_API_BASE_URL.replace(/\/+$/, "");

export const env = Object.freeze({
  apiBaseUrl,
  apiTimeout: parsed.data.VITE_API_TIMEOUT,
  appEnv: parsed.data.VITE_APP_ENV,
  siteUrl: parsed.data.VITE_SITE_URL.replace(/\/+$/, ""),
  isProduction: parsed.data.VITE_APP_ENV === "production",
  isDev: import.meta.env.DEV,
});

export type Env = typeof env;