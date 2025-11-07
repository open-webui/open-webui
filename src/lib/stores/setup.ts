// Setup flow state management for Tauri desktop app
import { writable, derived } from 'svelte/store';

export type CheckStatus = 'pending' | 'running' | 'success' | 'error' | 'skipped';

export interface SetupStep {
	id: string;
	label: string;
	status: CheckStatus;
	error?: string;
	progress?: number; // 0-100 for installation steps
}

export interface SetupState {
	currentStepIndex: number;
	steps: SetupStep[];
	isComplete: boolean;
	canRetry: boolean;
}

// Define the setup flow steps
const initialSteps: SetupStep[] = [
	{
		id: 'check_python',
		label: 'Checking bundled Python',
		status: 'pending'
	},
	{
		id: 'init_python_env',
		label: 'Initializing Python environment',
		status: 'pending'
	},
	{
		id: 'check_python_deps',
		label: 'Checking Python dependencies',
		status: 'pending'
	},
	{
		id: 'install_python_deps',
		label: 'Installing Python dependencies',
		status: 'pending',
		progress: 0
	},
	{
		id: 'check_ollama',
		label: 'Checking Ollama installation',
		status: 'pending'
	},
	{
		id: 'install_ollama',
		label: 'Installing Ollama',
		status: 'pending',
		progress: 0
	},
	{
		id: 'check_ollama_running',
		label: 'Checking if Ollama is running',
		status: 'pending'
	},
	{
		id: 'start_ollama',
		label: 'Starting Ollama',
		status: 'pending'
	},
	{
		id: 'check_ollama_model',
		label: 'Checking for llama3:8b model',
		status: 'pending'
	},
	{
		id: 'pull_ollama_model',
		label: 'Downloading llama3:8b model',
		status: 'pending',
		progress: 0
	},
	{
		id: 'start_backend',
		label: 'Starting backend server',
		status: 'pending'
	},
	{
		id: 'check_backend_health',
		label: 'Verifying backend health',
		status: 'pending'
	}
];

const initialState: SetupState = {
	currentStepIndex: 0,
	steps: initialSteps,
	isComplete: false,
	canRetry: false
};

// Create the setup store
function createSetupStore() {
	const { subscribe, set, update } = writable<SetupState>(initialState);

	return {
		subscribe,
		reset: () => set(initialState),

		// Move to the next step
		nextStep: () =>
			update((state) => ({
				...state,
				currentStepIndex: Math.min(state.currentStepIndex + 1, state.steps.length - 1)
			})),

		// Update a specific step's status
		updateStep: (stepId: string, updates: Partial<SetupStep>) =>
			update((state) => ({
				...state,
				steps: state.steps.map((step) =>
					step.id === stepId ? { ...step, ...updates } : step
				)
			})),

		// Set step to running
		setStepRunning: (stepId: string) =>
			update((state) => ({
				...state,
				steps: state.steps.map((step) =>
					step.id === stepId ? { ...step, status: 'running' as CheckStatus, error: undefined } : step
				)
			})),

		// Set step to success
		setStepSuccess: (stepId: string) =>
			update((state) => ({
				...state,
				steps: state.steps.map((step) =>
					step.id === stepId ? { ...step, status: 'success' as CheckStatus, error: undefined } : step
				)
			})),

		// Set step to skipped (e.g., if already installed)
		setStepSkipped: (stepId: string) =>
			update((state) => ({
				...state,
				steps: state.steps.map((step) =>
					step.id === stepId ? { ...step, status: 'skipped' as CheckStatus, error: undefined } : step
				)
			})),

		// Set step to error
		setStepError: (stepId: string, error: string) =>
			update((state) => ({
				...state,
				steps: state.steps.map((step) =>
					step.id === stepId ? { ...step, status: 'error' as CheckStatus, error } : step
				),
				canRetry: true
			})),

		// Update installation progress
		setProgress: (stepId: string, progress: number) =>
			update((state) => ({
				...state,
				steps: state.steps.map((step) =>
					step.id === stepId ? { ...step, progress: Math.min(100, Math.max(0, progress)) } : step
				)
			})),

		// Mark setup as complete
		complete: () =>
			update((state) => ({
				...state,
				isComplete: true
			})),

		// Get current step
		getCurrentStep: (state: SetupState): SetupStep | undefined => {
			return state.steps[state.currentStepIndex];
		}
	};
}

export const setupStore = createSetupStore();

// Derived store for current step
export const currentStep = derived(setupStore, ($setup) => $setup.steps[$setup.currentStepIndex]);

// Derived store for checking if any step has errors
export const hasErrors = derived(
	setupStore,
	($setup) => $setup.steps.some((step) => step.status === 'error')
);

// Derived store for overall progress percentage
export const overallProgress = derived(setupStore, ($setup) => {
	const completedSteps = $setup.steps.filter(
		(step) => step.status === 'success' || step.status === 'skipped'
	).length;
	return Math.round((completedSteps / $setup.steps.length) * 100);
});
