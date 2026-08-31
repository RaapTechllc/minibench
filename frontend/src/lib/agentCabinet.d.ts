export interface AgentCabinetCopy {
  tagline: string;
  notSoloNotMultiplayer: string;
  controlledVariables: string;
  presentationOrder: string;
  emptyTitle: string;
  emptyBody: string;
}

export interface ControlledVariablePayload {
  held_constant?: string[] | null;
  changed_variables?: string | null;
}

export const AGENT_CABINET_DEFAULT_FIELDS: readonly string[];
export const AGENT_CABINET_LIST_FIELDS: readonly string[];
export const AGENT_CABINET_TECHNICIAN_FIELDS: readonly string[];
export const AGENT_CABINET_COPY: Readonly<AgentCabinetCopy>;

export function categoryTitle(rawKey: string): string;
export function sortedCategoryEntries(
  categoryCompletion: Record<string, number> | null | undefined,
): [string, number][];
export function controlledVariableSentence(
  detail: ControlledVariablePayload | null | undefined,
): string;
