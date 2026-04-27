// 학습 세션 전역 상태 (Phase 0 — G-2)
import { writable } from 'svelte/store';
import type { LearningSessionState } from '$lib/types/learning';

export const learningSession = writable<LearningSessionState>({
	mode: 'default',
	currentHintStep: 0,
	totalHintSteps: 0,
	quizActive: false,
	problemStatement: undefined
});
