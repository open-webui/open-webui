<script lang="ts">
	import { getContext } from 'svelte';
	import { exportOverlay } from '$lib/stores';
	import type i18nType from '$lib/i18n';

	const i18n = getContext<typeof i18nType>('i18n');

	const onCancel = () => {
		$exportOverlay.onCancel?.();
	};

	$: estimatedMinutes = $exportOverlay.estimatedRemainingMinutes;
	$: exportStatus = estimatedMinutes ? $i18n.t('Exporting content. Estimated time: {{minutes}} min. Please wait...', {
		minutes: estimatedMinutes
	}) : $i18n.t('Exporting content. Please wait...');
</script>

{#if $exportOverlay.show}
	<div class="fixed inset-0 z-[10000] bg-black/50 flex items-center justify-center p-4">
		<div class="w-full max-w-md rounded-3xl bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-2xl p-5">
			<div class="text-base font-medium text-gray-900 dark:text-gray-100">
				{$i18n.t('Exporting PDF')}
			</div>

			<div class="mt-2 text-sm text-gray-600 dark:text-gray-300">
				{exportStatus}
			</div>

			<div class="mt-3 h-2 w-full rounded-full bg-gray-200 dark:bg-gray-800 overflow-hidden">
				<div
					class="h-full bg-gray-900 dark:bg-gray-100 transition-all duration-200"
					style={`width: ${Math.max(0, Math.min(100, $exportOverlay.progress))}%`}
				></div>
			</div>

			<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
				{Math.round($exportOverlay.progress)}%
				{#if $exportOverlay.totalChunks > 0}
					· {$i18n.t('Chunks')} {$exportOverlay.currentChunk}/{$exportOverlay.totalChunks}
				{/if}
				{#if $exportOverlay.pagesGenerated > 0}
					· {$i18n.t('Total')} {$exportOverlay.pagesGenerated} {$i18n.t('pages')}
				{/if}
			</div>

			<div class="mt-5 flex justify-end">
				<button
					type="button"
					class="px-4 py-2 text-sm rounded-2xl bg-gray-100 hover:bg-gray-200 text-gray-900 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-100"
					on:click={onCancel}
				>
					{$i18n.t('Cancel')}
				</button>
			</div>
		</div>
	</div>
{/if}
