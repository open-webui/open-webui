<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { setupStore, overallProgress, hasErrors } from '$lib/stores/setup';
	import {
		checkBundledPython,
		initializePythonEnvironment,
		checkPythonDependencies,
		installPythonDependencies,
		checkOllamaInstalled,
		installOllama,
		checkOllamaRunning,
		startOllama,
		startBackendServer,
		checkBackendHealth,
		isTauriApp
	} from '$lib/tauri-api';
	import CheckItem from '$lib/components/setup/CheckItem.svelte';
	import InstallProgress from '$lib/components/setup/InstallProgress.svelte';
	import SetupError from '$lib/components/setup/SetupError.svelte';

	let isRunning = false;
	let setupError: string | null = null;

	// Redirect if not in Tauri environment
	onMount(() => {
		if (!isTauriApp()) {
			// In browser mode, skip setup and go directly to main app
			goto('/');
			return;
		}

		// Start the setup process automatically
		runSetup();
	});

	async function runSetup() {
		if (isRunning) return;
		isRunning = true;
		setupError = null;
		setupStore.reset();

		try {
			// Step 1: Check bundled Python
			await runStep('check_python', 'Checking bundled Python', async () => {
				setupStore.setStepRunning('check_python');
				const hasPython = await checkBundledPython();
				if (hasPython) {
					setupStore.setStepSuccess('check_python');
				} else {
					throw new Error('Bundled Python 3.12 not found in app resources');
				}
			});

			// Step 2: Initialize Python environment
			await runStep('init_python_env', 'Initializing Python environment', async () => {
				setupStore.setStepRunning('init_python_env');
				await initializePythonEnvironment();
				setupStore.setStepSuccess('init_python_env');
			});

			// Step 3: Check Python dependencies
			let needsDepInstall = false;
			await runStep('check_python_deps', 'Checking Python dependencies', async () => {
				setupStore.setStepRunning('check_python_deps');
				const hasDeps = await checkPythonDependencies();
				if (hasDeps) {
					setupStore.setStepSuccess('check_python_deps');
					// Skip installation step
					setupStore.setStepSkipped('install_python_deps');
				} else {
					setupStore.setStepSuccess('check_python_deps');
					needsDepInstall = true;
				}
			});

			// Step 4: Install Python dependencies (if needed)
			if (needsDepInstall) {
				await runStep('install_python_deps', 'Installing Python dependencies', async () => {
					setupStore.setStepRunning('install_python_deps');
					// Simulate progress updates
					const progressInterval = setInterval(() => {
						const currentProgress = $setupStore.steps.find(s => s.id === 'install_python_deps')?.progress || 0;
						if (currentProgress < 90) {
							setupStore.setProgress('install_python_deps', currentProgress + 10);
						}
					}, 1000);

					try {
						await installPythonDependencies();
						clearInterval(progressInterval);
						setupStore.setProgress('install_python_deps', 100);
						setupStore.setStepSuccess('install_python_deps');
					} catch (error) {
						clearInterval(progressInterval);
						throw error;
					}
				});
			}

			// Step 5: Check Ollama installation
			let needsOllamaInstall = false;
			await runStep('check_ollama', 'Checking Ollama installation', async () => {
				setupStore.setStepRunning('check_ollama');
				const hasOllama = await checkOllamaInstalled();
				if (hasOllama) {
					setupStore.setStepSuccess('check_ollama');
					// Skip installation step
					setupStore.setStepSkipped('install_ollama');
				} else {
					setupStore.setStepSuccess('check_ollama');
					needsOllamaInstall = true;
				}
			});

			// Step 6: Install Ollama (if needed)
			if (needsOllamaInstall) {
				await runStep('install_ollama', 'Installing Ollama', async () => {
					setupStore.setStepRunning('install_ollama');
					// Simulate progress updates
					const progressInterval = setInterval(() => {
						const currentProgress = $setupStore.steps.find(s => s.id === 'install_ollama')?.progress || 0;
						if (currentProgress < 90) {
							setupStore.setProgress('install_ollama', currentProgress + 10);
						}
					}, 1000);

					try {
						await installOllama();
						clearInterval(progressInterval);
						setupStore.setProgress('install_ollama', 100);
						setupStore.setStepSuccess('install_ollama');
					} catch (error) {
						clearInterval(progressInterval);
						throw error;
					}
				});
			}

			// Step 7: Check if Ollama is running
			let needsOllamaStart = false;
			await runStep('check_ollama_running', 'Checking if Ollama is running', async () => {
				setupStore.setStepRunning('check_ollama_running');
				const isRunning = await checkOllamaRunning();
				if (isRunning) {
					setupStore.setStepSuccess('check_ollama_running');
					// Skip start step
					setupStore.setStepSkipped('start_ollama');
				} else {
					setupStore.setStepSuccess('check_ollama_running');
					needsOllamaStart = true;
				}
			});

			// Step 8: Start Ollama (if needed)
			if (needsOllamaStart) {
				await runStep('start_ollama', 'Starting Ollama', async () => {
					setupStore.setStepRunning('start_ollama');
					await startOllama();
					// Wait a moment for Ollama to start
					await new Promise(resolve => setTimeout(resolve, 2000));
					setupStore.setStepSuccess('start_ollama');
				});
			}

			// Step 9: Start backend server
			await runStep('start_backend', 'Starting backend server', async () => {
				setupStore.setStepRunning('start_backend');
				await startBackendServer();
				// Wait a moment for server to start
				await new Promise(resolve => setTimeout(resolve, 3000));
				setupStore.setStepSuccess('start_backend');
			});

			// Step 10: Verify backend health
			await runStep('check_backend_health', 'Verifying backend health', async () => {
				setupStore.setStepRunning('check_backend_health');
				
				// Retry health check up to 10 times with 1 second delay
				let healthy = false;
				for (let i = 0; i < 10; i++) {
					healthy = await checkBackendHealth();
					if (healthy) break;
					await new Promise(resolve => setTimeout(resolve, 1000));
				}

				if (healthy) {
					setupStore.setStepSuccess('check_backend_health');
				} else {
					throw new Error('Backend server failed to respond after multiple attempts');
				}
			});

			// Setup complete!
			setupStore.complete();
			
			// Navigate to main app
			setTimeout(() => {
				goto('/');
			}, 1000);

		} catch (error) {
			console.error('Setup error:', error);
			setupError = error instanceof Error ? error.message : String(error);
			isRunning = false;
		}
	}

	async function runStep(stepId: string, label: string, fn: () => Promise<void>) {
		try {
			await fn();
			setupStore.nextStep();
		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);
			setupStore.setStepError(stepId, errorMessage);
			throw error;
		}
	}

	function handleRetry() {
		runSetup();
	}

	function handleCancel() {
		// In a real app, you might want to close the application
		// For now, just log it
		console.log('Setup cancelled');
	}
</script>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-4">
	<div class="max-w-2xl w-full">
		<!-- Header -->
		<div class="text-center mb-8">
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
				Setting up Open WebUI
			</h1>
			<p class="text-gray-600 dark:text-gray-400">
				Please wait while we prepare your desktop application
			</p>
		</div>

		<!-- Main Setup Card -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
			<!-- Overall Progress Bar -->
			<div class="px-6 pt-6 pb-4">
				<div class="flex items-center justify-between mb-2">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Overall Progress</span>
					<span class="text-sm text-gray-600 dark:text-gray-400">{$overallProgress}%</span>
				</div>
				<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
					<div
						class="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
						style="width: {$overallProgress}%"
					></div>
				</div>
			</div>

			<!-- Setup Steps -->
			<div class="px-2 py-4 space-y-1 max-h-96 overflow-y-auto">
				{#each $setupStore.steps as step (step.id)}
					<CheckItem
						label={step.label}
						status={step.status}
						error={step.error}
					/>
					
					{#if step.status === 'running' && step.progress !== undefined}
						<InstallProgress
							label={step.label}
							progress={step.progress}
						/>
					{/if}
				{/each}
			</div>

			<!-- Error Display -->
			{#if setupError}
				<div class="px-2 pb-4">
					<SetupError
						error={setupError}
						onRetry={handleRetry}
						onCancel={handleCancel}
					/>
				</div>
			{/if}

			<!-- Completion Message -->
			{#if $setupStore.isComplete}
				<div class="px-6 py-4 bg-green-50 dark:bg-green-900/20 border-t border-green-200 dark:border-green-800">
					<div class="flex items-center">
						<svg class="h-6 w-6 text-green-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
						</svg>
						<div>
							<h3 class="text-sm font-medium text-green-800 dark:text-green-300">
								Setup Complete!
							</h3>
							<p class="text-sm text-green-700 dark:text-green-400 mt-1">
								Launching Open WebUI...
							</p>
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="text-center mt-6">
			<p class="text-xs text-gray-500 dark:text-gray-400">
				This process may take several minutes on first launch
			</p>
		</div>
	</div>
</div>

<style>
	/* Ensure smooth scrolling for the steps list */
	.overflow-y-auto {
		scrollbar-width: thin;
		scrollbar-color: rgba(156, 163, 175, 0.5) transparent;
	}

	.overflow-y-auto::-webkit-scrollbar {
		width: 6px;
	}

	.overflow-y-auto::-webkit-scrollbar-track {
		background: transparent;
	}

	.overflow-y-auto::-webkit-scrollbar-thumb {
		background-color: rgba(156, 163, 175, 0.5);
		border-radius: 3px;
	}
</style>
