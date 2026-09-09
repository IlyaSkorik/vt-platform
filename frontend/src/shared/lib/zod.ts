import { z } from "zod";

/**
 * The one `z` the app builds schemas from — configured to speak Russian.
 *
 * Zod's built-in messages ("Too big: expected string to have <=200 characters")
 * appear wherever a rule is declared without wording of its own, and they land in
 * the form beside the field like any other error. Zod ships a Russian locale, so
 * the fix is a single configuration rather than a message argument on every rule.
 *
 * Importing `z` from here rather than from `zod` is what applies it: the call runs
 * on module load, so a schema module that imports this cannot be evaluated before
 * the locale is in place — including in tests, which never load `main.tsx`.
 */
z.config(z.locales.ru());

export { z };
