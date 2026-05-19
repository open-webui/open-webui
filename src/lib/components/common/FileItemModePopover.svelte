<script lang="ts">
	import { createEventDispatcher, getContext, onMount, onDestroy } from 'svelte';
	import { fade } from 'svelte/transition';
	import { config } from '$lib/stores';
	import { updateFileProcessingMode } from '$lib/apis/files';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let mode: 'text' | 'pdf' = 'text';
	export let fileId: string | null = null;
	export let anchorEl: HTMLElement | null = null;
	export let isSpreadsheet = false;

	let containerEl: HTMLDivElement;

	$: pdfConversionAvailable = $config?.features?.pdf_conversion_available ?? true;

	const select = async (next: 'text' | 'pdf') => {
		if (next === mode) {
			dispatch('close');
			return;
		}

		if (next === 'pdf' && !pdfConversionAvailable) {
			toast.error(
				$i18n.t(
					'PDF conversion is unavailable on this server. Install LibreOffice to enable it.'
				)
			);
			return;
		}

		mode = next;
		dispatch('change', { mode: next });

		// Kick off background PDF conversion now so it has a head start on the
		// user's eventual send. The chat-completion lazy fallback still covers
		// the race if they send immediately.
		if (fileId) {
			try {
				await updateFileProcessingMode(localStorage.token, fileId, next);
			} catch (e) {
				console.error('Failed to update processing mode:', e);
			}
		}

		dispatch('close');
	};

	const onDocClick = (e: MouseEvent) => {
		if (!containerEl) return;
		const target = e.target as Node | null;
		if (target && containerEl.contains(target)) return;
		if (anchorEl && target && anchorEl.contains(target)) return;
		dispatch('close');
	};

	const onKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Escape') dispatch('close');
	};

	onMount(() => {
		// Defer to next tick so the click that opened us doesn't immediately close us.
		setTimeout(() => {
			document.addEventListener('mousedown', onDocClick);
			document.addEventListener('keydown', onKeydown);
		}, 0);
	});

	onDestroy(() => {
		document.removeEventListener('mousedown', onDocClick);
		document.removeEventListener('keydown', onKeydown);
	});
</script>

<div
	bind:this={containerEl}
	class="absolute z-50 mt-1 w-72 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-lg p-2.5 text-sm"
	transition:fade={{ duration: 80 }}
	role="dialog"
	aria-label={$i18n.t('Choose how to read this file')}
>
	<div class="text-xs text-gray-500 dark:text-gray-400 px-1.5 pb-1.5">
		{$i18n.t('How should the model read this file?')}
	</div>

	<button
		type="button"
		class="w-full text-left p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 flex items-start gap-2"
		on:click|stopPropagation={() => select('text')}
	>
		<span class="mt-0.5 size-4 shrink-0 rounded-full border border-gray-300 dark:border-gray-600 flex items-center justify-center">
			{#if mode === 'text'}
				<span class="size-2 rounded-full bg-current"></span>
			{/if}
		</span>
		<span class="flex-1">
			<span class="font-medium block">{$i18n.t('Extract text')}</span>
			<span class="text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t('Faster — but loses images, tables, and formatting.')}
			</span>
		</span>
	</button>

	<button
		type="button"
		class="w-full text-left p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 flex items-start gap-2 {pdfConversionAvailable
			? ''
			: 'opacity-50 cursor-not-allowed'}"
		on:click|stopPropagation={() => select('pdf')}
		disabled={!pdfConversionAvailable}
	>
		<span class="mt-0.5 size-4 shrink-0 rounded-full border border-gray-300 dark:border-gray-600 flex items-center justify-center">
			{#if mode === 'pdf'}
				<span class="size-2 rounded-full bg-current"></span>
			{/if}
		</span>
		<span class="flex-1">
			<span class="font-medium block">{$i18n.t('Convert to PDF')}</span>
			<span class="text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t('Slower — but preserves images, tables, and layout.')}
			</span>
			{#if isSpreadsheet}
				<span class="text-xs text-amber-600 dark:text-amber-400 block mt-1">
					{$i18n.t('Spreadsheets paginate poorly as PDFs. Text mode is usually better.')}
				</span>
			{/if}
			{#if !pdfConversionAvailable}
				<span class="text-xs text-amber-600 dark:text-amber-400 block mt-1">
					{$i18n.t('Unavailable: LibreOffice is not installed on the server.')}
				</span>
			{/if}
		</span>
	</button>
</div>
