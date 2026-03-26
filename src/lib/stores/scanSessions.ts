import { derived, get, writable } from 'svelte/store';

import type { Target } from '$lib/components/workspace/Targets/types';

export type ScanStageStatus = 'pending' | 'in_progress' | 'complete' | 'error';
export type ScanLifecycle = 'queued' | 'running' | 'paused' | 'complete' | 'error';

export type ScanStageId =
	| 'queued'
	| 'asset_validation'
	| 'surface_enumeration'
	| 'service_analysis'
	| 'findings_assembly'
	| 'complete';

export type ScanStage = {
	id: ScanStageId;
	label: string;
	status: ScanStageStatus;
};

export type ScanActivity = {
	id: string;
	timestamp: number;
	message: string;
	stageId: ScanStageId;
};

export type ScanSession = {
	id: string;
	targetId: string;
	targetName: string;
	lifecycle: ScanLifecycle;
	progress: number;
	startedAt: number;
	updatedAt: number;
	endedAt: number | null;
	currentStageId: ScanStageId;
	stages: ScanStage[];
	activity: ScanActivity[];
};

type ScanSessionMap = Record<string, ScanSession>;

type RuntimeSessionState = {
	intervalId: ReturnType<typeof setInterval>;
	stageIndex: number;
	stageProgress: number;
};

const SCAN_STAGES: Array<{ id: ScanStageId; label: string; weight: number }> = [
	{ id: 'queued', label: 'Queued', weight: 6 },
	{ id: 'asset_validation', label: 'Asset Validation', weight: 16 },
	{ id: 'surface_enumeration', label: 'Surface Enumeration', weight: 24 },
	{ id: 'service_analysis', label: 'Service Analysis', weight: 27 },
	{ id: 'findings_assembly', label: 'Findings Assembly', weight: 22 },
	{ id: 'complete', label: 'Complete', weight: 5 }
];

const RUNNING_STAGE_IDS: ScanStageId[] = [
	'asset_validation',
	'surface_enumeration',
	'service_analysis',
	'findings_assembly'
];

const STAGE_MESSAGES: Record<ScanStageId, string[]> = {
	queued: ['Target added to local scan queue.', 'Scan worker reserved for this target.'],
	asset_validation: [
		'Validating target metadata and connectivity assumptions.',
		'Normalizing target scope for enumeration stage.'
	],
	surface_enumeration: [
		'Enumerating reachable endpoints and externally visible assets.',
		'Collecting baseline response signatures from target surface.'
	],
	service_analysis: [
		'Inspecting exposed services and protocol fingerprints.',
		'Scoring service banners and transport characteristics.'
	],
	findings_assembly: [
		'Assembling generic mock findings summary for review.',
		'Consolidating stage artifacts into a final report draft.'
	],
	complete: ['Mock scan lifecycle completed successfully.']
};

const MOCK_ERROR_PROBABILITY = 0.08;
const MAX_ACTIVITY_ITEMS = 24;

const sessions = writable<ScanSessionMap>({});
const runtime = new Map<string, RuntimeSessionState>();

const now = () => Date.now();

const randomId = () =>
	typeof crypto !== 'undefined' && crypto.randomUUID
		? crypto.randomUUID()
		: `scan-${Date.now()}-${Math.floor(Math.random() * 10000)}`;

const randomInRange = (min: number, max: number) =>
	Math.floor(Math.random() * (max - min + 1)) + min;

const toStageRows = (): ScanStage[] =>
	SCAN_STAGES.map((stage, index) => ({
		id: stage.id,
		label: stage.label,
		status: index === 0 ? 'in_progress' : 'pending'
	}));

const totalRunningWeight = RUNNING_STAGE_IDS.reduce((sum, stageId) => {
	const stage = SCAN_STAGES.find((candidate) => candidate.id === stageId);
	return sum + (stage?.weight ?? 0);
}, 0);

const stopRuntime = (targetId: string) => {
	const state = runtime.get(targetId);
	if (!state) {
		return;
	}

	clearInterval(state.intervalId);
	runtime.delete(targetId);
};

const appendActivity = (
	session: ScanSession,
	stageId: ScanStageId,
	message: string
): ScanSession => {
	const nextActivity: ScanActivity = {
		id: randomId(),
		timestamp: now(),
		message,
		stageId
	};

	const activity = [...session.activity, nextActivity].slice(-MAX_ACTIVITY_ITEMS);
	return {
		...session,
		activity,
		updatedAt: nextActivity.timestamp
	};
};

const markStageStatus = (
	stages: ScanStage[],
	stageId: ScanStageId,
	status: ScanStageStatus
): ScanStage[] => stages.map((stage) => (stage.id === stageId ? { ...stage, status } : stage));

const weightedProgress = (stageIndex: number, stageProgress: number) => {
	const activeStageId = RUNNING_STAGE_IDS[stageIndex];
	const completedWeight = RUNNING_STAGE_IDS.slice(0, stageIndex).reduce((sum, stageId) => {
		const stage = SCAN_STAGES.find((candidate) => candidate.id === stageId);
		return sum + (stage?.weight ?? 0);
	}, 0);

	const activeWeight = SCAN_STAGES.find((stage) => stage.id === activeStageId)?.weight ?? 0;
	const runningPortion = completedWeight + activeWeight * stageProgress;
	const base = SCAN_STAGES.find((stage) => stage.id === 'queued')?.weight ?? 0;

	return Math.min(99, Math.round(base + (runningPortion / totalRunningWeight) * 89));
};

const setSession = (targetId: string, updater: (session: ScanSession) => ScanSession) => {
	sessions.update((current) => {
		const existing = current[targetId];
		if (!existing) {
			return current;
		}

		return {
			...current,
			[targetId]: updater(existing)
		};
	});
};

const startTicker = (targetId: string) => {
	stopRuntime(targetId);

	const intervalId = setInterval(() => {
		const current = get(sessions)[targetId];
		const runtimeState = runtime.get(targetId);
		if (!current || !runtimeState) {
			stopRuntime(targetId);
			return;
		}

		if (current.lifecycle !== 'running') {
			return;
		}

		const activeStageId = RUNNING_STAGE_IDS[runtimeState.stageIndex];
		if (!activeStageId) {
			return;
		}

		let stageProgress = Math.min(1, runtimeState.stageProgress + randomInRange(7, 13) / 100);
		runtimeState.stageProgress = stageProgress;

		if (
			activeStageId === 'service_analysis' &&
			stageProgress > 0.5 &&
			Math.random() < MOCK_ERROR_PROBABILITY
		) {
			setSession(targetId, (session) => {
				const failed = appendActivity(
					session,
					'service_analysis',
					'Mock signal indicates analysis instability. Escalating as demo error.'
				);
				return {
					...failed,
					lifecycle: 'error',
					currentStageId: 'service_analysis',
					progress: Math.max(failed.progress, 72),
					endedAt: now(),
					stages: markStageStatus(failed.stages, 'service_analysis', 'error'),
					updatedAt: now()
				};
			});
			stopRuntime(targetId);
			return;
		}

		if (stageProgress >= 1) {
			const completedStageId = activeStageId;
			runtimeState.stageIndex += 1;
			runtimeState.stageProgress = 0;

			const nextStageId = RUNNING_STAGE_IDS[runtimeState.stageIndex];
			if (!nextStageId) {
				setSession(targetId, (session) => {
					let nextSession = appendActivity(
						session,
						completedStageId,
						'Finalizing mock scan output package.'
					);
					nextSession = appendActivity(nextSession, 'complete', STAGE_MESSAGES.complete[0]);
					return {
						...nextSession,
						lifecycle: 'complete',
						progress: 100,
						currentStageId: 'complete',
						endedAt: now(),
						updatedAt: now(),
						stages: nextSession.stages.map((stage) => {
							if (stage.id === 'complete') {
								return { ...stage, status: 'complete' };
							}
							if (stage.id === completedStageId || RUNNING_STAGE_IDS.includes(stage.id)) {
								return { ...stage, status: 'complete' };
							}
							return stage;
						})
					};
				});
				stopRuntime(targetId);
				return;
			}

			setSession(targetId, (session) => {
				const progressed = appendActivity(
					session,
					nextStageId,
					STAGE_MESSAGES[nextStageId][randomInRange(0, STAGE_MESSAGES[nextStageId].length - 1)]
				);

				return {
					...progressed,
					currentStageId: nextStageId,
					progress: weightedProgress(runtimeState.stageIndex, 0),
					updatedAt: now(),
					stages: progressed.stages.map((stage) => {
						if (stage.id === completedStageId) {
							return { ...stage, status: 'complete' };
						}
						if (stage.id === nextStageId) {
							return { ...stage, status: 'in_progress' };
						}
						return stage;
					})
				};
			});

			return;
		}

		setSession(targetId, (session) => ({
			...session,
			progress: weightedProgress(runtimeState.stageIndex, stageProgress),
			updatedAt: now()
		}));
	}, 1100);

	runtime.set(targetId, { intervalId, stageIndex: 0, stageProgress: 0 });
};

export const scanSessions = derived(sessions, ($sessions) => $sessions);

export const startMockScanSession = (target: Target) => {
	const startedAt = now();
	const sessionId = randomId();

	stopRuntime(target.id);

	sessions.update((current) => ({
		...current,
		[target.id]: {
			id: sessionId,
			targetId: target.id,
			targetName: target.name,
			lifecycle: 'queued',
			progress: 4,
			startedAt,
			updatedAt: startedAt,
			endedAt: null,
			currentStageId: 'queued',
			stages: toStageRows(),
			activity: [
				{
					id: randomId(),
					timestamp: startedAt,
					message: STAGE_MESSAGES.queued[0],
					stageId: 'queued'
				}
			]
		}
	}));

	const promoteQueueTimeout = setTimeout(
		() => {
			const latest = get(sessions)[target.id];
			if (!latest || latest.id !== sessionId) {
				return;
			}

			sessions.update((current) => {
				const existing = current[target.id];
				if (!existing || existing.id !== sessionId || existing.lifecycle !== 'queued') {
					return current;
				}

				const nextStageId: ScanStageId = 'asset_validation';
				const next = appendActivity(
					existing,
					nextStageId,
					STAGE_MESSAGES[nextStageId][randomInRange(0, STAGE_MESSAGES[nextStageId].length - 1)]
				);

				return {
					...current,
					[target.id]: {
						...next,
						lifecycle: 'running',
						currentStageId: nextStageId,
						progress: 10,
						updatedAt: now(),
						stages: next.stages.map((stage) => {
							if (stage.id === 'queued') {
								return { ...stage, status: 'complete' };
							}
							if (stage.id === nextStageId) {
								return { ...stage, status: 'in_progress' };
							}
							return stage;
						})
					}
				};
			});

			startTicker(target.id);
		},
		randomInRange(1200, 2200)
	);

	setTimeout(() => {
		const latest = get(sessions)[target.id];
		if (!latest || latest.id !== sessionId || latest.lifecycle !== 'queued') {
			return;
		}

		clearTimeout(promoteQueueTimeout);
	}, 2400);
};

export const pauseMockScanSession = (targetId: string) => {
	const existing = get(sessions)[targetId];
	if (!existing || existing.lifecycle !== 'running') {
		return;
	}

	setSession(targetId, (session) =>
		appendActivity(
			{
				...session,
				lifecycle: 'paused',
				updatedAt: now(),
				stages: markStageStatus(session.stages, session.currentStageId, 'pending')
			},
			session.currentStageId,
			'Mock scan paused by operator.'
		)
	);
};

export const resumeMockScanSession = (targetId: string) => {
	const existing = get(sessions)[targetId];
	if (!existing || existing.lifecycle !== 'paused') {
		return;
	}

	setSession(targetId, (session) =>
		appendActivity(
			{
				...session,
				lifecycle: 'running',
				updatedAt: now(),
				stages: markStageStatus(session.stages, session.currentStageId, 'in_progress')
			},
			session.currentStageId,
			'Mock scan resumed and processing continues.'
		)
	);

	if (!runtime.get(targetId)) {
		startTicker(targetId);
	}
};

export const removeScanSession = (targetId: string) => {
	stopRuntime(targetId);
	sessions.update((current) => {
		if (!current[targetId]) {
			return current;
		}

		const next = { ...current };
		delete next[targetId];
		return next;
	});
};

export const getScanSessionForTarget = (targetId: string | null | undefined) => {
	if (!targetId) {
		return null;
	}

	return get(sessions)[targetId] ?? null;
};
