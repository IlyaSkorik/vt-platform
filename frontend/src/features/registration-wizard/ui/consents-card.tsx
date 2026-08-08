import { useEffect, useRef, useState } from "react";

import { useRecordConsents } from "@/entities/application";
import type { ApplicationResource } from "@/shared/api/generated/model-applications";
import type { Registration } from "@/shared/api/generated/model-public-catalog";
import { applicationConsent, ConsentCheckbox } from "@/shared/consents";
import { Alert, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui";

/**
 * Version recorded for a consent whose text the catalogue does not carry.
 *
 * Only reachable if a festival is configured with a code the frontend has never heard
 * of; recording *something* keeps the journal consistent, and the form still shows the
 * server's own label so the applicant sees what they are agreeing to.
 */
const FALLBACK_CONSENT_VERSION = "1.0";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Произошла ошибка. Попробуйте ещё раз.";
}

/** A stable fingerprint of "which consents are ticked", used to detect real changes. */
function signatureOf(
  required: Registration["requiredConsents"],
  accepted: Record<string, boolean>,
): string {
  return required
    .map((consent) => `${consent.code}:${accepted[consent.code] === true ? "1" : "0"}`)
    .sort()
    .join("|");
}

/**
 * The consents the festival asks for, autosaved as they are ticked.
 *
 * Shared by the wizard and the post-submission edit screen. Both the consents a
 * festival insists on and the ones it merely offers are shown: an elective consent
 * the applicant never sees is a consent they cannot give, which would make the
 * promise that a work is published only on request (LEGAL-001 §8.5) meaningless.
 */
export function ConsentsCard({
  applicationId,
  application,
  registration,
}: {
  applicationId: string;
  application: ApplicationResource;
  registration: Registration;
}): React.JSX.Element {
  const recordConsents = useRecordConsents(applicationId);
  const required = registration.requiredConsents;
  const recordedCodes = new Set(application.consents.map((consent) => consent.code));
  const [accepted, setAccepted] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(required.map((consent) => [consent.code, recordedCodes.has(consent.code)])),
  );
  // Seeded with what the server already holds, so merely opening the card saves
  // nothing. Left empty it would autosave once on mount every time — wasteful in the
  // wizard, and actively wrong on a submitted application, where that write is
  // journalled as an edit and reported to the organizer as a change nobody made.
  const autosavedSignature = useRef<string>(signatureOf(required, accepted));

  useEffect(() => {
    if (required.length === 0 || recordConsents.isPending) {
      return;
    }
    const signature = signatureOf(required, accepted);
    if (autosavedSignature.current === signature) {
      return;
    }
    autosavedSignature.current = signature;
    const handle = setTimeout(() => {
      recordConsents.mutate({
        consents: required
          .filter((consent) => accepted[consent.code] === true)
          .map((consent) => ({
            code: consent.code,
            // The version of the text that was actually displayed, from the same
            // catalogue that supplied the wording (LEGAL-001 §13.3).
            version: applicationConsent(consent.code)?.version ?? FALLBACK_CONSENT_VERSION,
          })),
      });
    }, 250);
    return () => clearTimeout(handle);
  }, [accepted, recordConsents, required]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>Согласия</CardTitle>
          <CardDescription>
            Согласия на обработку данных участника и на публикацию результатов обязательны;
            остальные — по решению фестиваля и по вашему желанию.
          </CardDescription>
        </div>
        <span className="min-h-5 text-xs text-muted-foreground">
          {recordConsents.isPending ? "Сохраняем…" : ""}
        </span>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {required.length === 0 ? (
          <p className="text-sm text-muted-foreground">Фестиваль не требует отдельных согласий.</p>
        ) : (
          required.map((consent) => {
            // The catalogue owns the wording; the projection only says whether this
            // festival asks for it. A code the catalogue does not know still renders,
            // from the label the server sent, rather than disappearing from the form.
            const definition = applicationConsent(consent.code) ?? {
              code: consent.code,
              version: FALLBACK_CONSENT_VERSION,
              required: consent.required,
              summary: consent.label,
              text: consent.label,
            };
            return (
              <ConsentCheckbox
                key={consent.code}
                consent={{ ...definition, required: consent.required }}
                checked={accepted[consent.code] === true}
                onChange={(checked) =>
                  setAccepted((prev) => ({ ...prev, [consent.code]: checked }))
                }
              />
            );
          })
        )}
        {recordConsents.isError ? (
          <Alert variant="danger">{errorMessage(recordConsents.error)}</Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}
