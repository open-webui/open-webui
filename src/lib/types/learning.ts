// 학습형 메시지 타입 정의 (Phase 0 — G-1)

export type LearningMessageType =
	| 'tutor' // 튜터형 구조화 응답
	| 'hint' // 단계별 힌트
	| 'quiz' // 퀴즈 문항
	| 'graph' // 그래프 포함 응답
	| 'feedback' // 오답 피드백 결과
	| 'session_summary'; // 세션 요약

export type ActionType = 'hint' | 'solve_myself' | 'similar_problem' | 'quiz' | 'graph';

export interface TutorMessage {
	type: 'tutor';
	summary: string;
	checkQuestion?: string;
	choices?: string[];
	actions?: ActionType[];
}

export interface HintStep {
	title: string;
	content: string;
}

export interface HintMessage {
	type: 'hint';
	totalSteps: number;
	currentStep: number;
	steps: HintStep[];
}

export interface QuizMessage {
	type: 'quiz';
	question: string;
	choices: string[];
	correctIndex: number;
	explanation: string;
}

export type GraphTemplate = 'function' | 'polar' | 'parametric' | 'vector_field';

export interface GraphMessage {
	type: 'graph';
	template: GraphTemplate;
	title: string;
	expression: string;
	params?: Record<string, number>;
}

export interface FeedbackResult {
	correctParts: string;
	errorStep?: string;
	errorTags: string[];
}

export type LearningMode = 'default' | 'hint' | 'quiz' | 'solve' | 'graph';

export interface LearningSessionState {
	mode: LearningMode;
	currentHintStep: number;
	totalHintSteps: number;
	quizActive: boolean;
	problemStatement?: string;
}
