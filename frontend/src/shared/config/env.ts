import { z } from "@/shared/lib/zod";

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

  VITE_APP_ENV: z.enum(["development", "stage", "production"]).default("development"),

  VITE_SITE_URL: z.url().default("https://vzlettalantov.by"),

  // Analytics counters. Empty (the default) means the counter is simply not wired
  // in this build — which is what every environment except production wants: a
  // developer's page views are not the audience anyone is measuring.
  VITE_YANDEX_METRICA_ID: z
    .string()
    .default("")
    .transform((v) => v.trim())
    .refine((v) => v === "" || /^\d+$/.test(v), "Must be empty or the numeric Metrica counter id"),

  VITE_GA_MEASUREMENT_ID: z
    .string()
    .default("")
    .transform((v) => v.trim())
    .refine(
      (v) => v === "" || /^G-[A-Z0-9]+$/i.test(v),
      "Must be empty or a GA4 measurement id (G-XXXXXXXXXX)",
    ),
});

const parsed = envSchema.safeParse(import.meta.env);

if (!parsed.success) {
  throw new Error(`Invalid environment configuration:\n${z.prettifyError(parsed.error)}`);
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
  /** Yandex Metrica counter id; `""` when this build carries no counter. */
  yandexMetricaId: parsed.data.VITE_YANDEX_METRICA_ID,
  /** GA4 measurement id; `""` when this build carries no counter. */
  googleAnalyticsId: parsed.data.VITE_GA_MEASUREMENT_ID,
});

export type Env = typeof env;
