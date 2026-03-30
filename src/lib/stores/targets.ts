import { derived, get, writable } from 'svelte/store';

import type { NewTargetInput, Target } from '$lib/components/workspace/Targets/types';
import {
	pauseScanSession,
	removeScanSession,
	resumeScanSession,
	scanSessions,
	startScanSession
} from '$lib/stores/scanSessions';

const initialTargets: Target[] = [];

export const targets = writable<Target[]>(initialTargets);
export const activeTargetId = writable<string | null>(initialTargets[0]?.id ?? null);
export const scanQueue = writable<string[]>([]);
export const isScanQueueRunning = writable(false);
export const activeQueueTargetId = writable<string | null>(null);

export const activeTarget = derived([targets, activeTargetId], ([$targets, $activeTargetId]) => {
	if (!$activeTargetId) {
		return null;
	}

	return $targets.find((target) => target.id === $activeTargetId) ?? null;
});

export const activeScanCount = derived(
	targets,
	($targets) => $targets.filter((target) => target.status === 'Active').length
);

const formatTimestamp = (value = new Date()) => {
	const pad = (value: number) => value.toString().padStart(2, '0');
	return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())} ${pad(value.getHours())}:${pad(value.getMinutes())}`;
};

let queueAdvanceTimer: ReturnType<typeof setTimeout> | null = null;

const clearQueueAdvanceTimer = () => {
	if (!queueAdvanceTimer) {
		return;
	}

	clearTimeout(queueAdvanceTimer);
	queueAdvanceTimer = null;
};

const triggerNextQueuedScan = () => {
	if (!get(isScanQueueRunning)) {
		return;
	}

	if (get(activeQueueTargetId)) {
		return;
	}

	const queue = get(scanQueue);
	const nextTargetId = queue[0];
	if (!nextTargetId) {
		isScanQueueRunning.set(false);
		return;
	}

	const target = get(targets).find((item) => item.id === nextTargetId);
	if (!target) {
		scanQueue.update((items) => items.filter((id) => id !== nextTargetId));
		triggerNextQueuedScan();
		return;
	}

	activeQueueTargetId.set(nextTargetId);
	setActiveTarget(nextTargetId);
	startScanSession(target);
};

scanSessions.subscribe(($scanSessions) => {
	targets.update((currentTargets) =>
		currentTargets.map((target) => {
			const session = $scanSessions[target.id];
			if (!session) {
				return target;
			}

			const nextStatus =
				session.lifecycle === 'queued'
					? 'Pending'
					: session.lifecycle === 'running'
						? 'Active'
						: session.lifecycle === 'paused'
							? 'Paused'
							: session.lifecycle === 'complete'
								? 'Complete'
								: 'Error';

			const nextLastScan =
				session.lifecycle === 'complete' || session.lifecycle === 'error'
					? formatTimestamp(new Date(session.endedAt ?? session.updatedAt))
					: target.lastScan;

			if (target.status === nextStatus && target.lastScan === nextLastScan) {
				return target;
			}

			return {
				...target,
				status: nextStatus,
				lastScan: nextLastScan
			};
		})
	);

	if (!get(isScanQueueRunning)) {
		return;
	}

	const currentQueueTarget = get(activeQueueTargetId);
	if (!currentQueueTarget) {
		triggerNextQueuedScan();
		return;
	}

	const currentSession = $scanSessions[currentQueueTarget];
	if (!currentSession) {
		return;
	}

	if (currentSession.lifecycle === 'complete' || currentSession.lifecycle === 'error') {
		scanQueue.update((items) => items.filter((id) => id !== currentQueueTarget));
		activeQueueTargetId.set(null);

		if (!queueAdvanceTimer) {
			queueAdvanceTimer = setTimeout(() => {
				queueAdvanceTimer = null;
				triggerNextQueuedScan();
			}, 700);
		}
	}
});

export const setActiveTarget = (id: string) => {
	activeTargetId.set(id);
};

export const addTarget = (payload: NewTargetInput) => {
	const id =
		typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `tgt-${Date.now()}`;

	targets.update((currentTargets) => [
		{
			id,
			name: payload.name,
			type: payload.type,
			value: payload.value,
			status: 'Pending',
			lastScan: null,
			description: payload.description
		},
		...currentTargets
	]);

	if (!get(activeTargetId)) {
		activeTargetId.set(id);
	}

	return id;
};

const inferTargetFromPrompt = (prompt: string): NewTargetInput => {
	const trimmed = prompt.trim();
	const safePrompt = trimmed.slice(0, 220);

	const urlMatch = trimmed.match(/https?:\/\/[^\s]+/i);
	if (urlMatch) {
		return {
			name: `Prompt URL Target`,
			type: 'URL',
			value: urlMatch[0],
			description: safePrompt || 'Generated from user prompt.'
		};
	}

	const cidrMatch = trimmed.match(/\b(?:\d{1,3}\.){3}\d{1,3}\/\d{1,2}\b/);
	if (cidrMatch) {
		return {
			name: `Prompt Network Target`,
			type: 'CIDR',
			value: cidrMatch[0],
			description: safePrompt || 'Generated from user prompt.'
		};
	}

	const ipMatch = trimmed.match(/\b(?:\d{1,3}\.){3}\d{1,3}\b/);
	if (ipMatch) {
		return {
			name: `Prompt IP Target`,
			type: 'IP',
			value: ipMatch[0],
			description: safePrompt || 'Generated from user prompt.'
		};
	}

	const domainMatch = trimmed.match(/\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b/);
	if (domainMatch) {
		return {
			name: `Prompt Domain Target`,
			type: 'Domain',
			value: domainMatch[0],
			description: safePrompt || 'Generated from user prompt.'
		};
	}

	const compact = trimmed.replace(/\s+/g, ' ').slice(0, 48);
	return {
		name: compact ? `Prompt Task: ${compact}` : 'Prompt Task Target',
		type: 'Host',
		value: 'prompt-task',
		description: safePrompt || 'Generated from user prompt.'
	};
};

export const createPromptTarget = (prompt: string) => {
	if (!prompt.trim()) {
		return null;
	}

	const id = addTarget(inferTargetFromPrompt(prompt));
	setActiveTarget(id);
	queueTargetScan(id);

	if (!get(isScanQueueRunning)) {
		startScanQueue();
	}

	return id;
};

export const queueTargetScan = (id: string) => {
	if (!get(targets).some((item) => item.id === id)) {
		return;
	}

	scanQueue.update((currentQueue) =>
		currentQueue.includes(id) ? currentQueue : [...currentQueue, id]
	);
	targets.update((currentTargets) =>
		currentTargets.map((target) =>
			target.id === id && target.status !== 'Active' && target.status !== 'Paused'
				? { ...target, status: 'Pending' }
				: target
		)
	);
};

export const removeFromScanQueue = (id: string) => {
	scanQueue.update((currentQueue) => currentQueue.filter((targetId) => targetId !== id));
	if (get(activeQueueTargetId) === id) {
		activeQueueTargetId.set(null);
	}
};

export const startScanQueue = () => {
	if (get(isScanQueueRunning) || get(scanQueue).length === 0) {
		return;
	}

	isScanQueueRunning.set(true);
	triggerNextQueuedScan();
};

export const stopScanQueue = () => {
	isScanQueueRunning.set(false);
	activeQueueTargetId.set(null);
	clearQueueAdvanceTimer();
};

export const toggleTargetStatus = (id: string) => {
	const target = get(targets).find((item) => item.id === id);
	if (!target) {
		return;
	}

	if (target.status === 'Active') {
		pauseScanSession(id);
		return;
	}

	if (target.status === 'Paused') {
		resumeScanSession(id);
		return;
	}

	targets.update((currentTargets) =>
		currentTargets.map((target) => {
			if (target.id !== id) {
				return target;
			}

			return {
				...target,
				status: target.status === 'Paused' ? 'Active' : 'Paused'
			};
		})
	);
};

export const deleteTarget = (id: string) => {
	removeScanSession(id);
	removeFromScanQueue(id);
	targets.update((currentTargets) => currentTargets.filter((target) => target.id !== id));

	if (get(activeTargetId) === id) {
		const remainingTargets = get(targets);
		activeTargetId.set(remainingTargets[0]?.id ?? null);
	}
};
