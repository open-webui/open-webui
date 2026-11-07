export type ToolApprovalMode = 'full' | 'ask' | 'auto';

export function resolveToolApprovalMode(value: unknown, autoEnabled = false): ToolApprovalMode {
	if (value == null) return autoEnabled ? 'auto' : 'full';
	if (value === 'auto') return autoEnabled ? 'auto' : 'ask';
	return value === 'full' || value === 'ask' ? value : 'ask';
}
