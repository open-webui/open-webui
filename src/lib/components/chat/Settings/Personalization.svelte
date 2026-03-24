<script lang="ts">
	import { getBackendConfig } from '$lib/apis';
	import { setDefaultPromptSuggestions } from '$lib/apis/configs';
	import Switch from '$lib/components/common/Switch.svelte';
	import { config, models, settings, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import ManageModal from './Personalization/ManageModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	let showManageModal = false;

	// Addons
	let enableMemory = false;

	onMount(async () => {
		enableMemory = $settings?.memory ?? false;
	});
</script>

<ManageModal bind:show={showManageModal} />

<form
	class="flex flex-col h-full justify-between"
	on:submit|preventDefault={() => {
		dispatch('save');
	}}
>
	<div class="space-y-4 sm:space-y-6 overflow-y-auto">
		<!-- Memory Section -->
		<div class="space-y-3 sm:space-y-4">
			<div>
				<h3 class="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('Memory')}
				</h3>
				<p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
					Personalize your interactions with AI assistants
				</p>
			</div>

			<!-- Memory Toggle Card -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 sm:p-4">
				<div class="flex items-center justify-between">
					<div class="flex-1">
						<div class="flex items-center gap-2">
							<div class="text-xs sm:text-sm font-medium text-gray-900 dark:text-white">
								{$i18n.t('Enable Memory')}
							</div>
							<Tooltip
								content={$i18n.t(
									'This is an experimental feature, it may not function as expected and is subject to change at any time.'
								)}
							>
								<span
									class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 border border-yellow-200 dark:border-yellow-800"
								>
									{$i18n.t('Experimental')}
								</span>
							</Tooltip>
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							Allow AI to remember context from past conversations
						</div>
					</div>
					<Switch
						bind:state={enableMemory}
						on:change={async () => {
							saveSettings({ memory: enableMemory });
						}}
					/>
				</div>
			</div>

			<!-- Description Box -->
			<div
				class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 sm:p-4"
			>
				<div class="flex gap-2 sm:gap-3">
					<div class="flex-shrink-0">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5 text-blue-600 dark:text-blue-400"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"
							/>
						</svg>
					</div>
					<div class="flex-1">
						<div class="text-xs sm:text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">
							How it works
						</div>
						<div class="text-xs text-blue-800 dark:text-blue-200">
							{$i18n.t(
								"You can personalize your interactions with LLMs by adding memories through the 'Manage' button below, making them more helpful and tailored to you."
							)}
						</div>
					</div>
				</div>
			</div>

			<!-- Manage Button -->
			<div class="flex justify-start">
				<button
					type="button"
					class="w-full sm:w-auto inline-flex items-center justify-center sm:justify-start gap-2 px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
					on:click={() => {
						showManageModal = true;
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="w-4 h-4"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75"
						/>
					</svg>
					{$i18n.t('Manage')}
				</button>
			</div>

			<!-- Example Interactions (Optional - Commented in original) -->
			<!-- <div
				class="bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
			>
				<div class="flex gap-3">
					<div class="flex-shrink-0">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-5 h-5 text-gray-600 dark:text-gray-400"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"
							/>
						</svg>
					</div>
					<div class="flex-1">
						<div class="text-sm font-medium text-gray-900 dark:text-white mb-2">
							Example interactions
						</div>
						<div class="text-xs text-gray-600 dark:text-gray-400 space-y-1.5">
							<div class="flex items-start gap-2">
								<span class="text-gray-400 dark:text-gray-500">•</span>
								<span>"Remember that I like concise responses."</span>
							</div>
							<div class="flex items-start gap-2">
								<span class="text-gray-400 dark:text-gray-500">•</span>
								<span>"I just got a puppy!"</span>
							</div>
							<div class="flex items-start gap-2">
								<span class="text-gray-400 dark:text-gray-500">•</span>
								<span>"What do you remember about me?"</span>
							</div>
							<div class="flex items-start gap-2">
								<span class="text-gray-400 dark:text-gray-500">•</span>
								<span>"Where did we leave off on my last project?"</span>
							</div>
						</div>
					</div>
				</div>
			</div> -->
		</div>
	</div>

	<!-- Save Button -->
	<div class="flex justify-end pt-4 sm:pt-6 border-t border-gray-200 dark:border-gray-700 mt-4 sm:mt-6">
		<button
			class="w-full sm:w-auto px-4 sm:px-6 py-2 sm:py-2.5 text-xs sm:text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>

<style>
	/* Custom scrollbar styling */
	::-webkit-scrollbar {
		width: 8px;
		height: 8px;
	}

	::-webkit-scrollbar-track {
		background: transparent;
	}

	::-webkit-scrollbar-thumb {
		background: rgba(156, 163, 175, 0.5);
		border-radius: 4px;
	}

	::-webkit-scrollbar-thumb:hover {
		background: rgba(156, 163, 175, 0.7);
	}

	:global(.dark) ::-webkit-scrollbar-thumb {
		background: rgba(75, 85, 99, 0.5);
	}

	:global(.dark) ::-webkit-scrollbar-thumb:hover {
		background: rgba(75, 85, 99, 0.7);
	}
</style>