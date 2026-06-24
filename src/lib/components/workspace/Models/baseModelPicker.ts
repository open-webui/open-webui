import type { Model } from '$lib/stores';

export type BaseModelPickerContext = {
	editingModelId?: string | null;
};

/**
 * Layer B metadata gate: model payloads expose connection_type, owned_by, direct,
 * name, id, and tags. There is no verified per-connection display name on the model
 * object, so connection-name-level grouping requires a separate API/store contract.
 * Degraded owner/type grouping would add little beyond existing Selector chips.
 */
export const BASE_MODEL_PICKER_LAYER_B_DECISION = 'no-go' as const;

export const isEligibleBaseModel = (
	candidate: Model,
	context: BaseModelPickerContext = {}
): boolean =>
	(!context.editingModelId || candidate.id !== context.editingModelId) &&
	!candidate?.preset &&
	!(candidate?.arena ?? false) &&
	candidate?.owned_by !== 'arena';

export const toBaseModelSelectorValue = (baseModelId: string | null | undefined): string =>
	baseModelId ?? '';

export const fromBaseModelSelectorValue = (value: string): string | null => value || null;

export const normalizeSavedBaseModelId = (
	savedId: string | null | undefined,
	models: Model[],
	context: BaseModelPickerContext = {}
): string | null => {
	if (!savedId) {
		return null;
	}

	const match = models
		.filter((candidate) => isEligibleBaseModel(candidate, context))
		.find((candidate) => [savedId, `${savedId}:latest`].includes(candidate.id));

	return match?.id ?? null;
};

export const buildBaseModelPickerItems = (models: Model[], context: BaseModelPickerContext = {}) =>
	models
		.filter((candidate) => isEligibleBaseModel(candidate, context))
		.map((candidate) => ({
			value: candidate.id,
			label: candidate.name,
			model: candidate
		}));
