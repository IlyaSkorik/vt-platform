import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { UseFormRegisterReturn } from "react-hook-form";
import {
  type AutosaveState,
  contactsConfigToPayload,
  resolveContactsConfig,
  useUpdateContactsConfigurationMutation,
} from "@/features/competitions";
import { ApiError } from "@/shared/api";
import type {
  _ContactsConfig,
  _VenueDetails,
  CompetitionDetail,
} from "@/shared/api/generated/model-competitions";
import { Card, CardContent, Input, PageSection, Textarea, toast } from "@/shared/ui";

const AUTOSAVE_DELAY_MS = 600;

interface VenueSectionProps {
  competition: CompetitionDetail;
  isReadOnly: boolean;
  nameField: UseFormRegisterReturn;
  addressField: UseFormRegisterReturn;
  nameError?: string | undefined;
  addressError?: string | undefined;
  onAutosaveStateChange: (state: AutosaveState) => void;
}

/**
 * The festival's venue, in full: where it happens and how to get there.
 *
 * Two data sources meet here. Name and address belong to the competition itself
 * and travel with the General form's own autosave, so they arrive as registered
 * fields. The rest (city, country, maps, directions) live in the contacts
 * configuration and are saved by this component on their own debounce — the same
 * arrangement the section had while it lived under «Контакты».
 */
export function VenueSection({
  competition,
  isReadOnly,
  nameField,
  addressField,
  nameError,
  addressError,
  onAutosaveStateChange,
}: VenueSectionProps): React.JSX.Element {
  const updateConfig = useUpdateContactsConfigurationMutation();
  const config = useMemo(() => resolveContactsConfig(competition), [competition]);
  const [details, setDetails] = useState<_VenueDetails>(config.venueDetails);

  // The committed config, so a save can carry the untouched parts of it (team
  // contacts, emergency, the organization override) alongside the edited venue.
  const configRef = useRef<_ContactsConfig>(config);
  // Edits still on their way to the server: without this, the refetch that follows
  // a save would overwrite whatever was typed in the meantime.
  const isDirtyRef = useRef(false);
  const saveGeneration = useRef(0);
  const autosaveTimer = useRef<number | null>(null);

  useEffect(() => {
    configRef.current = config;
    if (isDirtyRef.current) {
      return;
    }
    setDetails(config.venueDetails);
  }, [config]);

  useEffect(
    () => () => {
      if (autosaveTimer.current != null) {
        window.clearTimeout(autosaveTimer.current);
      }
    },
    [],
  );

  const persist = useCallback(
    async (next: _VenueDetails) => {
      saveGeneration.current += 1;
      const generation = saveGeneration.current;
      onAutosaveStateChange("saving");
      try {
        await updateConfig.mutateAsync({
          competitionId: competition.id,
          payload: contactsConfigToPayload({ ...configRef.current, venueDetails: next }),
        });
        if (generation !== saveGeneration.current) {
          return;
        }
        isDirtyRef.current = false;
        onAutosaveStateChange("saved");
      } catch (error) {
        if (generation !== saveGeneration.current) {
          return;
        }
        onAutosaveStateChange("error");
        toast.error(
          error instanceof ApiError
            ? (error.problem?.detail ?? "Не удалось сохранить площадку")
            : "Не удалось сохранить площадку",
        );
      }
    },
    [competition.id, onAutosaveStateChange, updateConfig],
  );

  const updateDetails = useCallback(
    (patch: Partial<_VenueDetails>) => {
      if (isReadOnly) {
        return;
      }
      const next = { ...details, ...patch };
      setDetails(next);
      isDirtyRef.current = true;
      onAutosaveStateChange("dirty");
      if (autosaveTimer.current != null) {
        window.clearTimeout(autosaveTimer.current);
      }
      autosaveTimer.current = window.setTimeout(() => {
        void persist(next);
      }, AUTOSAVE_DELAY_MS);
    },
    [details, isReadOnly, onAutosaveStateChange, persist],
  );

  return (
    <PageSection title="Площадка" description="Где проходит фестиваль и как добраться.">
      <Card className="shadow-none">
        <CardContent className="space-y-4 pt-6">
          <div className="grid gap-4 md:grid-cols-2">
            <Input
              label="Название площадки"
              disabled={isReadOnly}
              {...(nameError != null ? { error: nameError } : {})}
              {...nameField}
            />
            <Input
              label="Адрес"
              disabled={isReadOnly}
              {...(addressError != null ? { error: addressError } : {})}
              {...addressField}
            />
            <Input
              label="Город"
              disabled={isReadOnly}
              value={details.city ?? ""}
              onChange={(event) => updateDetails({ city: event.target.value })}
            />
            <Input
              label="Страна"
              disabled={isReadOnly}
              value={details.country ?? ""}
              onChange={(event) => updateDetails({ country: event.target.value })}
            />
            <Input
              label="Google Maps"
              disabled={isReadOnly}
              value={details.googleMapsUrl ?? ""}
              onChange={(event) => updateDetails({ googleMapsUrl: event.target.value })}
            />
            <Input
              label="Яндекс Карты"
              disabled={isReadOnly}
              value={details.yandexMapsUrl ?? ""}
              onChange={(event) => updateDetails({ yandexMapsUrl: event.target.value })}
            />
          </div>
          <Textarea
            label="Как добраться"
            disabled={isReadOnly}
            value={details.directions ?? ""}
            onChange={(event) => updateDetails({ directions: event.target.value })}
          />
        </CardContent>
      </Card>
    </PageSection>
  );
}
