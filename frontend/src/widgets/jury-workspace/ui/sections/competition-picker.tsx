import { useMemo, useState } from "react";

import { useCompetitionsList } from "@/features/competitions";
import { Select, type SelectOption } from "@/shared/ui";

/**
 * "Какой фестиваль" — asked once, at the top, for the whole section.
 *
 * The same shape the protocols section settled on and for the same reason: an organizer
 * works on one festival at a time, and putting that question inside every subsequent
 * action turns a glance into a form. Lifted out of that section so the four screens
 * added around it ask it identically.
 */
export function useCompetitionPicker(): {
  competitionId: string;
  picker: React.JSX.Element;
} {
  const [competitionId, setCompetitionId] = useState("");
  const competitionsQuery = useCompetitionsList();

  const options: SelectOption[] = useMemo(
    () => (competitionsQuery.data ?? []).map((item) => ({ value: item.id, label: item.title })),
    [competitionsQuery.data],
  );

  const picker = (
    <Select
      label="Фестиваль"
      placeholder="Выберите фестиваль"
      options={options}
      value={competitionId}
      onValueChange={setCompetitionId}
      containerClassName="max-w-md"
    />
  );

  return { competitionId, picker };
}
