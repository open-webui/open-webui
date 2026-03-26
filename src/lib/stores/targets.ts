import { derived, get, writable } from 'svelte/store';

import type { NewTargetInput, Target } from '$lib/components/workspace/Targets/types';
import {
	pauseMockScanSession,
	removeScanSession,
	resumeMockScanSession,
	scanSessions,
	startMockScanSession
} from '$lib/stores/scanSessions';

const initialTargets: Target[] = [
	{
		id: 'tgt-001',
		name: 'Corporate Web Tier',
		type: 'Domain',
		value: 'corp.example.com',
		status: 'Active',
		lastScan: '2026-03-09 22:14',
		description: 'Public web entrypoint and auth surfaces.'
	},
	{
		id: 'tgt-002',
		name: 'Primary API Gateway',
		type: 'URL',
		value: 'https://api.example.com/v1',
		status: 'Pending',
		lastScan: '2026-03-08 18:43',
		description: 'REST gateway used by mobile and partner clients.'
	},
	{
		id: 'tgt-003',
		name: 'Branch Office Range',
		type: 'CIDR',
		value: '10.24.0.0/16',
		status: 'Paused',
		lastScan: null,
		description: 'Network inventory target for staged internal validation.'
	},
	{
		id: 'tgt-004',
		name: 'Legacy Jumpbox',
		type: 'IP',
		value: '172.16.12.44',
		status: 'Error',
		lastScan: '2026-03-07 09:31',
		description: 'Known intermittent host requiring manual review.'
	}
];

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
	startMockScanSession(target);
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
		pauseMockScanSession(id);
		return;
	}

	if (target.status === 'Paused') {
		resumeMockScanSession(id);
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
