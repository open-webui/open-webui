/**
 * Web Search readiness helpers.
 *
 * Open WebUI exposes Web Search as a per-model capability, but gives no signal about whether
 * a given *local* model is actually likely to do agentic Web Search well. These helpers
 * compute a best-effort readiness signal from metadata already available in the frontend
 * (Ollama parameter size and `num_ctx`). They are intentionally:
 *   - warning-only: they never block or change behavior;
 *   - decoupled & pure: they return stable codes + numbers, never translated text, so the UI
 *     layer owns the wording (and i18n);
 *   - conservative: unknown metadata yields "unknown" (never a false warning), and non-local
 *     (API) models are always treated as ready.
 */

// Parameter-size thresholds, in billions of parameters. These are a practical quality signal,
// not a hard technical boundary, and are kept here so they are easy to review and tune.
export const WEB_SEARCH_READY_MIN_B = 14; // >= 14B: not warned ("usable" and up)
export const WEB_SEARCH_RECOMMENDED_MIN_B = 30; // >= 30B: "recommended" wording

// Context-length thresholds, in tokens. Only applied when the context length is known.
export const WEB_SEARCH_CTX_ACCEPTABLE = 8192; // < 8192: limited
export const WEB_SEARCH_CTX_STRONG_WARN = 4096; // < 4096: strong warning

export type WebSearchReadinessState = 'ready' | 'limited' | 'unknown' | 'disabled';

export type WebSearchReason =
	| 'capability_disabled'
	| 'size_low'
	| 'size_experimental'
	| 'size_usable'
	| 'size_recommended'
	| 'size_unknown'
	| 'context_low'
	| 'context_limited'
	| 'context_unknown';

export type WebSearchReadiness = {
	state: WebSearchReadinessState;
	reasons: WebSearchReason[];
	parameterSizeB: number | null;
	contextLength: number | null;
};

// Minimal structural shape so this stays decoupled from the full Model union and works for
// both Ollama list entries and resolved/base models.
type ModelLike = {
	id?: string;
	owned_by?: string;
	details?: { parameter_size?: string | null } | null;
	ollama?: { details?: { parameter_size?: string | null } | null } | null;
};

/**
 * Parse an Ollama parameter-size string into billions of parameters.
 * Examples: "7B" -> 7, "7.6B" -> 7.6, "8x7B" -> 56, "350M" -> 0.35. Returns null if unparseable.
 */
export function parseParameterSizeString(value?: string | null): number | null {
	if (!value) {
		return null;
	}

	const normalized = value.toLowerCase().replace(/\s+/g, '');

	// Mixture-of-experts notation, e.g. "8x7b" -> 8 * 7 = 56B (total parameters).
	const moe = normalized.match(/^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)b$/);
	if (moe) {
		return parseFloat(moe[1]) * parseFloat(moe[2]);
	}

	// Plain notation, e.g. "7b", "7.6b", "350m".
	const plain = normalized.match(/^(\d+(?:\.\d+)?)([bm])$/);
	if (plain) {
		const amount = parseFloat(plain[1]);
		return plain[2] === 'm' ? amount / 1000 : amount;
	}

	return null;
}

/**
 * Best-effort extraction of a size token from a model id, e.g. "llama3.1:8b" -> 8,
 * "mixtral:8x7b" -> 56. Only used as a fallback when explicit metadata is missing.
 */
function parseParameterSizeFromId(id?: string): number | null {
	if (!id) {
		return null;
	}

	const token = id
		.toLowerCase()
		.match(/(?:^|[-:_/])(\d+(?:\.\d+)?x\d+(?:\.\d+)?b|\d+(?:\.\d+)?b)(?:[-:_/]|$)/);
	return token ? parseParameterSizeString(token[1]) : null;
}

/**
 * Resolve a model's parameter size (in billions) from the metadata Open WebUI exposes for
 * Ollama models, falling back to the model id. Returns null when it cannot be determined.
 */
export function parseModelParameterSize(model?: ModelLike | null): number | null {
	if (!model) {
		return null;
	}

	const fromMeta =
		parseParameterSizeString(model.ollama?.details?.parameter_size) ??
		parseParameterSizeString(model.details?.parameter_size);

	return fromMeta ?? parseParameterSizeFromId(model.id);
}

/**
 * Compute a best-effort Web Search readiness signal for a model. Pure and side-effect-free.
 * Non-local (API) models are always "ready"; unknown local metadata yields "unknown" rather
 * than a warning.
 */
export function getWebSearchReadiness(args: {
	isLocal: boolean;
	parameterSizeB: number | null;
	contextLength: number | null;
	capabilityEnabled: boolean;
}): WebSearchReadiness {
	const { isLocal, parameterSizeB, contextLength, capabilityEnabled } = args;

	if (!capabilityEnabled) {
		return { state: 'disabled', reasons: ['capability_disabled'], parameterSizeB, contextLength };
	}

	// API / non-local models: we cannot (and need not) assess local strength.
	if (!isLocal) {
		return { state: 'ready', reasons: [], parameterSizeB, contextLength };
	}

	const reasons: WebSearchReason[] = [];

	let sizeState: 'ready' | 'limited' | 'unknown';
	if (parameterSizeB == null) {
		sizeState = 'unknown';
		reasons.push('size_unknown');
	} else if (parameterSizeB < 7) {
		sizeState = 'limited';
		reasons.push('size_low');
	} else if (parameterSizeB < WEB_SEARCH_READY_MIN_B) {
		sizeState = 'limited';
		reasons.push('size_experimental');
	} else if (parameterSizeB < WEB_SEARCH_RECOMMENDED_MIN_B) {
		sizeState = 'ready';
		reasons.push('size_usable');
	} else {
		sizeState = 'ready';
		reasons.push('size_recommended');
	}

	let ctxState: 'ready' | 'limited' | 'unknown';
	if (contextLength == null) {
		ctxState = 'unknown';
		reasons.push('context_unknown');
	} else if (contextLength < WEB_SEARCH_CTX_STRONG_WARN) {
		ctxState = 'limited';
		reasons.push('context_low');
	} else if (contextLength < WEB_SEARCH_CTX_ACCEPTABLE) {
		ctxState = 'limited';
		reasons.push('context_limited');
	} else {
		ctxState = 'ready';
	}

	let state: WebSearchReadinessState;
	if (sizeState === 'limited' || ctxState === 'limited') {
		state = 'limited';
	} else if (sizeState === 'unknown' && ctxState === 'unknown') {
		state = 'unknown';
	} else {
		state = 'ready';
	}

	return { state, reasons, parameterSizeB, contextLength };
}
