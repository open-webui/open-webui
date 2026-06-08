const PENDING_OAUTH_TOOL_ID_KEY = 'pendingOAuthToolId';
const PENDING_OAUTH_SELECTED_MODELS_KEY = 'pendingOAuthSelectedModels';

export type PendingOAuthState = {
	toolId: string | null;
	selectedModels: string[] | null;
};

const canUseSessionStorage = () => typeof sessionStorage !== 'undefined';

export const savePendingOAuthState = ({
	toolId,
	selectedModels
}: {
	toolId: string;
	selectedModels: string[];
}) => {
	if (!canUseSessionStorage()) {
		return;
	}

	sessionStorage.setItem(PENDING_OAUTH_TOOL_ID_KEY, toolId);
	sessionStorage.setItem(
		PENDING_OAUTH_SELECTED_MODELS_KEY,
		JSON.stringify(selectedModels.filter((id) => id))
	);
};

export const consumePendingOAuthState = (): PendingOAuthState => {
	if (!canUseSessionStorage()) {
		return { toolId: null, selectedModels: null };
	}

	const toolId = sessionStorage.getItem(PENDING_OAUTH_TOOL_ID_KEY);
	const selectedModelsString = sessionStorage.getItem(PENDING_OAUTH_SELECTED_MODELS_KEY);

	if (toolId) {
		sessionStorage.removeItem(PENDING_OAUTH_TOOL_ID_KEY);
	}
	if (selectedModelsString) {
		sessionStorage.removeItem(PENDING_OAUTH_SELECTED_MODELS_KEY);
	}

	let selectedModels: string[] | null = null;
	if (selectedModelsString) {
		try {
			const parsed = JSON.parse(selectedModelsString);
			if (Array.isArray(parsed)) {
				selectedModels = parsed.filter((id) => typeof id === 'string' && id);
			}
		} catch {
			selectedModels = null;
		}
	}

	return { toolId, selectedModels };
};

export const applyPendingOAuthState = ({
	availableModels,
	selectedModels,
	selectedToolIds,
	pendingState
}: {
	availableModels: string[];
	selectedModels: string[];
	selectedToolIds: string[];
	pendingState: PendingOAuthState;
}) => {
	const nextSelectedModels =
		pendingState.selectedModels && pendingState.selectedModels.length > 0
			? pendingState.selectedModels.filter((modelId) => availableModels.includes(modelId))
			: selectedModels;

	const nextSelectedToolIds =
		pendingState.toolId && !selectedToolIds.includes(pendingState.toolId)
			? [...selectedToolIds, pendingState.toolId]
			: selectedToolIds;

	return {
		selectedModels: nextSelectedModels,
		selectedToolIds: nextSelectedToolIds
	};
};
