import type { RealtimeClientConfig } from '$lib/apis/audio';

export function getEffectiveRealtimeModelId(
	model?: any | null,
	fallbackModelId?: string | null
): string {
	const infoBaseModelId = model?.info?.base_model_id;
	if (typeof infoBaseModelId === 'string' && infoBaseModelId) {
		return infoBaseModelId;
	}

	const baseModelId = model?.base_model_id;
	if (typeof baseModelId === 'string' && baseModelId) {
		return baseModelId;
	}

	const modelId = fallbackModelId ?? model?.id;
	return typeof modelId === 'string' ? modelId : '';
}

export function modelLooksRealtimeCapable(
	model?: any | null,
	fallbackModelId?: string | null
): boolean {
	return getEffectiveRealtimeModelId(model, fallbackModelId).toLowerCase().includes('realtime');
}

const getQualifiedRealtimeModelIds = (
	realtimeClientConfig?: RealtimeClientConfig | null
): Set<string> => {
	if (!realtimeClientConfig?.enabled) {
		return new Set();
	}

	return new Set(
		(realtimeClientConfig.capabilities?.models ?? []).map((modelId) => modelId.toLowerCase())
	);
};

export function modelUsesRealtime(
	model?: any | null,
	fallbackModelId?: string | null,
	realtimeClientConfig?: RealtimeClientConfig | null
): boolean {
	const effectiveModelId = getEffectiveRealtimeModelId(model, fallbackModelId).toLowerCase();
	if (!effectiveModelId) {
		return false;
	}

	return getQualifiedRealtimeModelIds(realtimeClientConfig).has(effectiveModelId);
}

export function modelHasRealtimeCapability(
	models: Array<any>,
	modelId?: string | null,
	realtimeClientConfig?: RealtimeClientConfig | null
): boolean {
	if (!modelId) {
		return false;
	}

	const model = models.find((candidate) => candidate.id === modelId) ?? null;
	return modelUsesRealtime(model, modelId, realtimeClientConfig);
}
