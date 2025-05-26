<script lang="ts">
	import { settings } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { PiiSessionManager } from '$lib/utils/pii';
	import { createPiiSession } from '$lib/apis/pii';

	let enablePiiDetection = $settings?.piiDetection?.enabled ?? false;
	let piiApiKey = $settings?.piiDetection?.apiKey ?? '';
	let isTestingConnection = false;
	let connectionStatus = '';

	const piiSessionManager = PiiSessionManager.getInstance();

	const testConnection = async () => {
		if (!piiApiKey.trim()) {
			toast.error('Please enter a valid API key');
			return;
		}

		isTestingConnection = true;
		connectionStatus = '';

		try {
			const session = await createPiiSession(piiApiKey, '1h');
			if (session.session_id) {
				connectionStatus = 'success';
				toast.success('PII API connection successful');
				piiSessionManager.setApiKey(piiApiKey);
				piiSessionManager.setSession(session.session_id);
			}
		} catch (error: any) {
			connectionStatus = 'error';
			toast.error(`Failed to connect to PII API: ${error?.message || 'Unknown error'}`);
		} finally {
			isTestingConnection = false;
		}
	};

	export let saveSettings: Function;

	const savePiiSettings = () => {
		saveSettings({
			piiDetection: {
				enabled: enablePiiDetection,
				apiKey: piiApiKey
			}
		});

		if (enablePiiDetection && piiApiKey) {
			piiSessionManager.setApiKey(piiApiKey);
		}

		toast.success('PII detection settings saved');
	};
</script>

<div class="flex flex-col space-y-4">
	<div class="flex items-center justify-between">
		<div class="flex flex-col">
			<div class="text-sm font-medium">Enable PII Detection</div>
			<div class="text-xs text-gray-500">
				Automatically detect and mask personally identifiable information in messages
			</div>
		</div>
		<label class="relative inline-flex items-center cursor-pointer">
			<input
				type="checkbox"
				bind:checked={enablePiiDetection}
				class="sr-only peer"
				on:change={savePiiSettings}
			/>
			<div
				class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"
			></div>
		</label>
	</div>

	{#if enablePiiDetection}
		<div class="space-y-3">
			<div class="flex flex-col space-y-2">
				<label for="pii-api-key" class="text-sm font-medium">
					NENNA API Key
				</label>
				<div class="flex space-x-2">
					<input
						id="pii-api-key"
						type="password"
						bind:value={piiApiKey}
						placeholder="Enter your NENNA API key"
						class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						on:blur={savePiiSettings}
					/>
					<button
						type="button"
						on:click={testConnection}
						disabled={isTestingConnection || !piiApiKey.trim()}
						class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg transition-colors duration-200 flex items-center space-x-2"
					>
						{#if isTestingConnection}
							<svg
								class="animate-spin h-4 w-4"
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
							>
								<circle
									class="opacity-25"
									cx="12"
									cy="12"
									r="10"
									stroke="currentColor"
									stroke-width="4"
								></circle>
								<path
									class="opacity-75"
									fill="currentColor"
									d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
								></path>
							</svg>
						{:else}
							<span>Test</span>
						{/if}
					</button>
				</div>
				
				{#if connectionStatus === 'success'}
					<div class="text-sm text-green-600 dark:text-green-400 flex items-center space-x-1">
						<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
							<path
								fill-rule="evenodd"
								d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
								clip-rule="evenodd"
							/>
						</svg>
						<span>Connection successful</span>
					</div>
				{:else if connectionStatus === 'error'}
					<div class="text-sm text-red-600 dark:text-red-400 flex items-center space-x-1">
						<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
							<path
								fill-rule="evenodd"
								d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
								clip-rule="evenodd"
							/>
						</svg>
						<span>Connection failed</span>
					</div>
				{/if}
			</div>

			<div class="text-xs text-gray-500 space-y-1">
				<p>Get your API key from <a href="https://nenna.ai" target="_blank" class="text-blue-600 hover:underline">nenna.ai</a></p>
				<p>PII detection will highlight sensitive information in your messages and mask it before sending to the AI model.</p>
			</div>
		</div>
	{/if}
</div> 