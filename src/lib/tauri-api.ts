// Tauri API wrapper for desktop app system checks and operations
import { invoke } from '@tauri-apps/api/core';

export interface SetupProgress {
	percentage: number;
	message?: string;
}

export interface SetupError {
	step: string;
	message: string;
	retryable: boolean;
}

export interface AppPreferences {
	auto_start_ollama: boolean;
	keep_ollama_running_on_exit: boolean;
	backend_port: number;
}

export interface ServiceStatus {
	ollama: {
		running: boolean;
		process_managed: boolean;
	};
	backend: {
		running: boolean;
		process_managed: boolean;
	};
}

// ========== Python Environment ==========

/**
 * Check if bundled Python 3.12 exists in app resources
 */
export async function checkBundledPython(): Promise<boolean> {
	try {
		return await invoke<boolean>('check_bundled_python');
	} catch (error) {
		console.error('Failed to check bundled Python:', error);
		throw error;
	}
}

/**
 * Initialize Python virtual environment using bundled Python
 */
export async function initializePythonEnvironment(): Promise<void> {
	try {
		await invoke('initialize_python_environment');
	} catch (error) {
		console.error('Failed to initialize Python environment:', error);
		throw error;
	}
}

/**
 * Check if Python dependencies are installed in the venv
 */
export async function checkPythonDependencies(): Promise<boolean> {
	try {
		return await invoke<boolean>('check_python_dependencies');
	} catch (error) {
		console.error('Failed to check Python dependencies:', error);
		throw error;
	}
}

/**
 * Install Python dependencies to the bundled venv
 * @param onProgress - Callback for installation progress updates
 */
export async function installPythonDependencies(
	onProgress?: (progress: SetupProgress) => void
): Promise<void> {
	try {
		// TODO: Implement progress callback when Tauri command supports it
		await invoke('install_python_dependencies');
	} catch (error) {
		console.error('Failed to install Python dependencies:', error);
		throw error;
	}
}

// ========== Ollama ==========

/**
 * Check if Ollama is installed on the system
 */
export async function checkOllamaInstalled(): Promise<boolean> {
	try {
		return await invoke<boolean>('check_ollama_installed');
	} catch (error) {
		console.error('Failed to check Ollama installation:', error);
		throw error;
	}
}

/**
 * Install Ollama on the system
 * @param onProgress - Callback for installation progress updates
 */
export async function installOllama(onProgress?: (progress: SetupProgress) => void): Promise<void> {
	try {
		// TODO: Implement progress callback when Tauri command supports it
		await invoke('install_ollama');
	} catch (error) {
		console.error('Failed to install Ollama:', error);
		throw error;
	}
}

/**
 * Check if Ollama service is running
 */
export async function checkOllamaRunning(): Promise<boolean> {
	try {
		return await invoke<boolean>('check_ollama_running');
	} catch (error) {
		console.error('Failed to check Ollama status:', error);
		throw error;
	}
}

/**
 * Start the Ollama service
 */
export async function startOllama(): Promise<void> {
	try {
		await invoke('start_ollama');
	} catch (error) {
		console.error('Failed to start Ollama:', error);
		throw error;
	}
}

/**
 * Check if an Ollama model is installed
 * @param modelName - Model name (e.g., "llama3:8b")
 */
export async function checkOllamaModel(modelName: string): Promise<boolean> {
	try {
		return await invoke<boolean>('check_ollama_model', { modelName });
	} catch (error) {
		console.error('Failed to check Ollama model:', error);
		throw error;
	}
}

/**
 * Pull/download an Ollama model
 * @param modelName - Model name (e.g., "llama3:8b")
 */
export async function pullOllamaModel(modelName: string): Promise<void> {
	try {
		await invoke('pull_ollama_model', { modelName });
	} catch (error) {
		console.error('Failed to pull Ollama model:', error);
		throw error;
	}
}

// ========== Backend Server ==========

/**
 * Start the FastAPI backend server using bundled Python
 */
export async function startBackendServer(): Promise<void> {
	try {
		await invoke('start_backend_server');
	} catch (error) {
		console.error('Failed to start backend server:', error);
		throw error;
	}
}

/**
 * Check if backend server is healthy and responding
 */
export async function checkBackendHealth(): Promise<boolean> {
	try {
		return await invoke<boolean>('check_backend_health');
	} catch (error) {
		console.error('Failed to check backend health:', error);
		throw error;
	}
}

// ========== Utility Functions ==========

/**
 * Get the platform-specific app data directory path
 */
export async function getAppDataPath(): Promise<string> {
	try {
		return await invoke<string>('get_app_data_path');
	} catch (error) {
		console.error('Failed to get app data path:', error);
		throw error;
	}
}

/**
 * Check if running in Tauri environment
 */
export function isTauriApp(): boolean {
	return typeof window !== 'undefined' && '__TAURI__' in window;
}

// ========== Preferences ==========

/**
 * Get app preferences
 */
export async function getPreferences(): Promise<AppPreferences> {
	try {
		return await invoke<AppPreferences>('get_preferences');
	} catch (error) {
		console.error('Failed to get preferences:', error);
		throw error;
	}
}

/**
 * Update app preferences
 */
export async function updatePreferences(preferences: AppPreferences): Promise<void> {
	try {
		await invoke('update_preferences', { preferences });
	} catch (error) {
		console.error('Failed to update preferences:', error);
		throw error;
	}
}

// ========== Lifecycle Management ==========

/**
 * Stop the backend server
 */
export async function stopBackendServer(): Promise<void> {
	try {
		await invoke('stop_backend_server');
	} catch (error) {
		console.error('Failed to stop backend server:', error);
		throw error;
	}
}

/**
 * Stop Ollama service
 */
export async function stopOllama(): Promise<void> {
	try {
		await invoke('stop_ollama');
	} catch (error) {
		console.error('Failed to stop Ollama:', error);
		throw error;
	}
}

/**
 * Restart backend and related services
 */
export async function restartServices(): Promise<void> {
	try {
		await invoke('restart_services');
	} catch (error) {
		console.error('Failed to restart services:', error);
		throw error;
	}
}

/**
 * Get current service status
 */
export async function getServiceStatus(): Promise<ServiceStatus> {
	try {
		return await invoke<ServiceStatus>('get_service_status');
	} catch (error) {
		console.error('Failed to get service status:', error);
		throw error;
	}
}
