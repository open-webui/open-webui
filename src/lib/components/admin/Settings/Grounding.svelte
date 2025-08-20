<script lang="ts">
	import WikipediaGroundingConfig from './grounding/WikipediaGroundingConfig.svelte';
	import { updateRAGConfig } from '$lib/apis/retrieval';
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let wikipediaConfig = { enabled: false };
	let loading = false;

	const handleSubmit = async () => {
		loading = true;

		try {
			const res = await updateRAGConfig(localStorage.token, {
				enable_wikipedia_grounding: wikipediaConfig.enabled
			});

			if (res) {
				toast.success($i18n.t('Settings saved successfully!'));
				// Call the parent save handler
				if (saveHandler) {
					await saveHandler();
				}
			} else {
				toast.error($i18n.t('Failed to save settings'));
			}
		} catch (error) {
			console.error('Error saving grounding settings:', error);
			toast.error($i18n.t('An error occurred while saving settings'));
		} finally {
			loading = false;
		}
	};
</script>

<form class="flex flex-col h-full space-y-4 text-sm" on:submit|preventDefault={handleSubmit}>
	<!-- Header -->
	<div class="space-y-2">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
			{$i18n.t('Knowledge Grounding')}
		</h2>
		<p class="text-sm text-gray-600 dark:text-gray-400">
			{$i18n.t(
				'Configure external knowledge sources to enhance AI responses with current, factual information.'
			)}
		</p>
	</div>

	<!-- Grounding Sources -->
	<div class="space-y-4 overflow-y-auto scrollbar-hidden flex-1">
		<!-- Wikipedia Grounding -->
		<WikipediaGroundingConfig bind:config={wikipediaConfig} />

		<!-- Future grounding sources will be added here -->
		<!-- <ScholarGroundingConfig bind:config={scholarConfig} /> -->
		<!-- <NewsGroundingConfig bind:config={newsConfig} /> -->
		<!-- <CustomGroundingConfig bind:config={customConfig} /> -->

		<!-- Placeholder for future sources -->
		<div
			class="bg-gray-50 dark:bg-gray-800 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 p-6 text-center"
		>
			<div class="text-gray-500 dark:text-gray-400">
				<svg class="mx-auto h-8 w-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M12 6v6m0 0v6m0-6h6m-6 0H6"
					/>
				</svg>
				<p class="text-sm font-medium">{$i18n.t('More grounding sources coming soon')}</p>
				<p class="text-xs mt-1">
					{$i18n.t('Academic papers, news, custom databases, and more...')}
				</p>
			</div>
		</div>
	</div>

	<!-- Save Button -->
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full disabled:opacity-50"
			type="submit"
			disabled={loading}
		>
			{#if loading}
				<svg class="w-3.5 h-3.5 animate-spin mr-2 inline" viewBox="0 0 24 24" fill="currentColor">
					<path
						d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
						opacity=".25"
					/>
					<path
						d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
						class="spinner_ajPY"
					/>
				</svg>
				{$i18n.t('Saving...')}
			{:else}
				{$i18n.t('Save')}
			{/if}
		</button>
	</div>
</form>

<style>
	.spinner_ajPY {
		transform-origin: center;
		animation: spinner_AtaB 0.75s infinite linear;
	}
	@keyframes spinner_AtaB {
		100% {
			transform: rotate(360deg);
		}
	}
</style>
