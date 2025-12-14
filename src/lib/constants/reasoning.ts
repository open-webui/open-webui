import type { ExtraReasoningEffort, ReasoningEffort } from '$lib/apis';

export const REASONING_EFFORT_ORDER: ReasoningEffort[] = [
	'none',
	'minimal',
	'low',
	'medium',
	'high',
	'xhigh'
];

export const BASE_REASONING_EFFORTS: ReasoningEffort[] = ['low', 'medium', 'high'];
export const EXTRA_REASONING_EFFORTS: ExtraReasoningEffort[] = ['none', 'minimal', 'xhigh'];

export const orderReasoningEfforts = (efforts: ReasoningEffort[] | (ReasoningEffort | string)[]) =>
	REASONING_EFFORT_ORDER.filter((effort) => efforts.includes(effort));
