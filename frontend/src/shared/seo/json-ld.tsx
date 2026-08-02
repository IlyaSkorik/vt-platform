import { useEffect } from "react";

/**
 * Structured data — what turns a blue link into a rich result.
 *
 * Rendered into the head imperatively for the same reason the meta tags are:
 * one tag per page, replaced rather than accumulated across navigations. The
 * payload is `unknown` on purpose — schema.org shapes are open-ended, and the
 * builders in `structured-data.ts` are where the shape is actually decided.
 */
export function JsonLd({ id, data }: { id: string; data: unknown }): null {
  // Serialized in the body of the effect, not on render: the value is a plain
  // object rebuilt on every render, so serializing is what makes the dependency
  // comparable and keeps the effect from re-running for an unchanged graph.
  const payload = JSON.stringify(data);

  useEffect(() => {
    const element = document.createElement("script");
    element.type = "application/ld+json";
    element.dataset.jsonLd = id;
    // `<` is the only character that can break out of a script element; escaping
    // it keeps a competition titled with an angle bracket from ending the tag.
    element.textContent = payload.replace(/</g, "\\u003c");
    document.head.appendChild(element);
    return () => element.remove();
  }, [id, payload]);

  return null;
}
