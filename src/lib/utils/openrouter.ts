const VALID_PRESETS = new Set(['fast', 'smart', 'code']);
const VALID_SORTS = new Set(['latency', 'price', 'throughput']);

const parseCsv = (value: unknown): string[] => {
	if (typeof value !== 'string') {
		return [];
	}

	return value
		.split(',')
		.map((v) => v.trim())
		.filter((v) => v.length > 0);
};

const parseJsonSchema = (raw: unknown): Record<string, unknown> | null => {
	if (!raw || typeof raw !== 'string' || raw.trim() === '') {
		return null;
	}

	try {
		const parsed = JSON.parse(raw);
		if (parsed && typeof parsed === 'object') {
			return parsed as Record<string, unknown>;
		}
	} catch {
		return null;
	}

	return null;
};

export const buildOpenRouterMetadata = (openrouter: any): Record<string, unknown> | undefined => {
	if (!openrouter || typeof openrouter !== 'object') {
		return undefined;
	}

	const metadata: Record<string, unknown> = {
		data_collection: 'deny'
	};

	const preset = `${openrouter.preset ?? ''}`.trim().toLowerCase();
	if (VALID_PRESETS.has(preset)) {
		metadata.preset = preset;
	}

	const providerSort = `${openrouter.provider_sort ?? ''}`.trim().toLowerCase();
	if (VALID_SORTS.has(providerSort)) {
		metadata.provider_sort = providerSort;
	}

	if (openrouter.zdr_sensitive === true) {
		metadata.sensitive = true;
	}

	if (openrouter.streaming === false) {
		metadata.non_stream = true;
	}

	if (openrouter.non_stream_fallback === true) {
		metadata.non_stream_fallback = true;
	}

	if (openrouter.json_output === true) {
		metadata.json_output = true;
		const schema = parseJsonSchema(openrouter.json_schema);
		if (schema) {
			metadata.json_schema = {
				name: 'openrouter_ui_schema',
				schema
			};
		}

		metadata.enable_response_healing = openrouter.response_healing !== false;
	}

	const guardrailAllowedModels = parseCsv(openrouter.guardrail_allowed_models);
	if (guardrailAllowedModels.length > 0) {
		metadata.guardrail_allowed_models = guardrailAllowedModels;
	}

	const guardrailAllowedProviders = parseCsv(openrouter.guardrail_allowed_providers);
	if (guardrailAllowedProviders.length > 0) {
		metadata.guardrail_allowed_providers = guardrailAllowedProviders;
	}

	const guardrailMaxTokensRaw = `${openrouter.guardrail_max_tokens ?? ''}`.trim();
	if (guardrailMaxTokensRaw !== '') {
		const guardrailMaxTokens = Number.parseInt(guardrailMaxTokensRaw, 10);
		if (!Number.isNaN(guardrailMaxTokens) && guardrailMaxTokens > 0) {
			metadata.guardrail_max_tokens = guardrailMaxTokens;
		}
	}

	if (typeof openrouter.guardrail_hard_fail === 'boolean') {
		metadata.guardrail_hard_fail = openrouter.guardrail_hard_fail;
	}

	const payloadKeys = Object.keys(metadata).filter((k) => k !== 'data_collection');
	if (payloadKeys.length === 0) {
		return undefined;
	}

	return {
		openrouter: metadata
	};
};
