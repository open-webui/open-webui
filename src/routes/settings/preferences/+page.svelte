<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		getPreferences,
		updatePreferences,
		getServiceStatus,
		restartServices,
		isTauriApp,
		type AppPreferences,
		type ServiceStatus
	} from '$lib/tauri-api';

	let preferences: AppPreferences = {
		auto_start_ollama: true,
		keep_ollama_running_on_exit: true,
		backend_port: 8080
	};

	let serviceStatus: ServiceStatus | null = null;
	let loading = false;
	let saving = false;
	let restarting = false;
	let saveMessage = '';

	onMount(async () => {
		if (!isTauriApp()) {
			// Not in Tauri, redirect to main settings
			goto('/settings');
			return;
		}

		await loadPreferences();
		await loadServiceStatus();
	});

	async function loadPreferences() {
		loading = true;
		try {
			preferences = await getPreferences();
		} catch (error) {
			console.error('Failed to load preferences:', error);
		} finally {
			loading = false;
		}
	}

	async function loadServiceStatus() {
		try {
			serviceStatus = await getServiceStatus();
		} catch (error) {
			console.error('Failed to load service status:', error);
		}
	}

	async function handleSave() {
		saving = true;
		saveMessage = '';
		try {
			await updatePreferences(preferences);
			saveMessage = 'Settings saved successfully!';
			setTimeout(() => {
				saveMessage = '';
			}, 3000);
		} catch (error) {
			console.error('Failed to save preferences:', error);
			saveMessage = 'Failed to save settings';
		} finally {
			saving = false;
		}
	}

	async function handleRestart() {
		if (!confirm('This will restart the backend server. Continue?')) {
			return;
		}

		restarting = true;
		try {
			await restartServices();
			await new Promise((resolve) => setTimeout(resolve, 3000));
			await loadServiceStatus();
			alert('Services restarted successfully!');
		} catch (error) {
			console.error('Failed to restart services:', error);
			alert('Failed to restart services');
		} finally {
			restarting = false;
		}
	}
</script>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
	<div class="max-w-4xl mx-auto">
		<!-- Header -->
		<div class="mb-8">
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
				Desktop App Preferences
			</h1>
			<p class="text-gray-600 dark:text-gray-400">
				Configure settings for the Open WebUI desktop application
			</p>
		</div>

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<div class="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
			</div>
		{:else}
			<!-- Service Status Card -->
			{#if serviceStatus}
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
						Service Status
					</h2>

					<div class="space-y-3">
						<!-- Ollama Status -->
						<div class="flex items-center justify-between">
							<span class="text-gray-700 dark:text-gray-300">Ollama</span>
							<div class="flex items-center gap-2">
								<span
									class="px-3 py-1 text-sm rounded-full {serviceStatus.ollama.running
										? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
										: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}"
								>
									{serviceStatus.ollama.running ? 'Running' : 'Stopped'}
								</span>
							</div>
						</div>

						<!-- Backend Status -->
						<div class="flex items-center justify-between">
							<span class="text-gray-700 dark:text-gray-300">Backend Server</span>
							<div class="flex items-center gap-2">
								<span
									class="px-3 py-1 text-sm rounded-full {serviceStatus.backend.running
										? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
										: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}"
								>
									{serviceStatus.backend.running ? 'Running' : 'Stopped'}
								</span>
							</div>
						</div>
					</div>

					<!-- Restart Button -->
					<div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
						<button
							type="button"
							class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
							on:click={handleRestart}
							disabled={restarting}
						>
							{#if restarting}
								<span class="flex items-center gap-2">
									<svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
									Restarting...
								</span>
							{:else}
								Restart Services
							{/if}
						</button>
					</div>
				</div>
			{/if}

			<!-- Settings Card -->
			<div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-6">Settings</h2>

				<form on:submit|preventDefault={handleSave} class="space-y-6">
					<!-- Auto-start Ollama -->
					<div class="flex items-start">
						<div class="flex items-center h-6">
							<input
								id="auto-start-ollama"
								type="checkbox"
								bind:checked={preferences.auto_start_ollama}
								class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600 dark:focus:ring-blue-600"
							/>
						</div>
						<label for="auto-start-ollama" class="ml-3 block">
							<span class="text-sm font-medium text-gray-900 dark:text-white">
								Auto-start Ollama
							</span>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								Automatically start Ollama when the app launches if it's not already running
							</p>
						</label>
					</div>

					<!-- Keep Ollama Running -->
					<div class="flex items-start">
						<div class="flex items-center h-6">
							<input
								id="keep-ollama-running"
								type="checkbox"
								bind:checked={preferences.keep_ollama_running_on_exit}
								class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600 dark:focus:ring-blue-600"
							/>
						</div>
						<label for="keep-ollama-running" class="ml-3 block">
							<span class="text-sm font-medium text-gray-900 dark:text-white">
								Keep Ollama running on exit
							</span>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								Leave Ollama running in the background when you close the app (only applies if the app started Ollama)
							</p>
						</label>
					</div>

					<!-- Backend Port -->
					<div>
						<label for="backend-port" class="block text-sm font-medium text-gray-900 dark:text-white mb-2">
							Backend Port
						</label>
						<input
							id="backend-port"
							type="number"
							bind:value={preferences.backend_port}
							min="1024"
							max="65535"
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
						/>
						<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
							Port for the backend server (default: 8080). Changes require a restart.
						</p>
					</div>

					<!-- Save Message -->
					{#if saveMessage}
						<div
							class="px-4 py-3 rounded-md {saveMessage.includes('success')
								? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200'
								: 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200'}"
						>
							{saveMessage}
						</div>
					{/if}

					<!-- Actions -->
					<div class="flex items-center gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
						<button
							type="submit"
							class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
							disabled={saving}
						>
							{saving ? 'Saving...' : 'Save Settings'}
						</button>

						<button
							type="button"
							class="px-6 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-md transition-colors"
							on:click={() => goto('/settings')}
						>
							Back to Settings
						</button>
					</div>
				</form>
			</div>
		{/if}
	</div>
</div>
