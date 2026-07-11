import { MapPin, Radio, Wifi } from "lucide-react";
import type { ParticipationMode } from "./types";

export interface ParticipationModeConfig {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const CONFIG: Record<ParticipationMode, ParticipationModeConfig> = {
  IN_PERSON: { label: "Очно", icon: MapPin },
  ONLINE: { label: "Онлайн", icon: Wifi },
  HYBRID: { label: "Гибрид", icon: Radio },
};

/** Every mode, in a stable display order — used to render filter controls. */
export const PARTICIPATION_MODES: ParticipationMode[] = ["IN_PERSON", "ONLINE", "HYBRID"];

export function participationModeConfig(mode: string): ParticipationModeConfig | null {
  return CONFIG[mode as ParticipationMode] ?? null;
}

export function participationModeLabel(mode: string): string {
  return participationModeConfig(mode)?.label ?? mode;
}
