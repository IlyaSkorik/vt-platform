/**
 * Tidying for the parts of a person's name — фамилия, имя, отчество.
 *
 * People type names in a hurry: caps lock left on, a stray double space, a
 * lowercase first letter. The registry then prints those names on diplomas and
 * protocols, so it is worth fixing the shape at the point of entry rather than
 * asking an organizer to hunt for "ИВАНОВ" later.
 *
 * Deliberately scoped to people. A collective's name ("ДЮСШ №2", "Ансамбль
 * ЛАДА") carries capitalisation the author meant, and must never pass through
 * here.
 */

/** Characters that start a new capitalised part inside one word: Петров-Водкин, О'Нил. */
const WORD_INNER_SEPARATORS = /([-'’])/;

/** Capitalises one run of letters, lowercasing whatever follows. */
function capitalizeWord(word: string): string {
  if (!word) return word;
  return word.charAt(0).toLocaleUpperCase("ru") + word.slice(1).toLocaleLowerCase("ru");
}

/**
 * Formats a single name part: first letter of each word up, the rest down,
 * with runs of whitespace collapsed and the edges trimmed.
 *
 * Returns the input untouched when it holds no letters, so that a field a user
 * is midway through clearing does not get rewritten under them.
 */
export function formatPersonName(value: string): string {
  const collapsed = value.trim().replace(/\s+/g, " ");
  if (!collapsed) return "";
  return collapsed
    .split(" ")
    .map((word) => word.split(WORD_INNER_SEPARATORS).map(capitalizeWord).join(""))
    .join(" ");
}
