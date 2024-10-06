<script>
	import { onDestroy, onMount, tick, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import Markdown from './Markdown.svelte';
	import LightBlub from '$lib/components/icons/LightBlub.svelte';
	import { mobile, showArtifacts, showControls, showOverview } from '$lib/stores';

	export let id;
	export let content;
	export let model = null;

	export let save = false;
	export let floatingButtons = true;

	let contentContainerElement;
	let buttonsContainerElement;

	const updateButtonPosition = (event) => {
		setTimeout(async () => {
			await tick();

			// Check if the event target is within the content container
			if (!contentContainerElement?.contains(event.target)) return;

			let selection = window.getSelection();

			if (selection.toString().trim().length > 0) {
				const range = selection.getRangeAt(0);
				const rect = range.getBoundingClientRect();
				const parentRect = contentContainerElement.getBoundingClientRect();

				// Adjust based on parent rect
				const top = rect.bottom - parentRect.top;
				const left = rect.left - parentRect.left;
				if (buttonsContainerElement) {
					buttonsContainerElement.style.display = 'block';
					buttonsContainerElement.style.left = `${left}px`;
					buttonsContainerElement.style.top = `${top + 5}px`; // +5 to add some spacing
				}
			} else {
				if (buttonsContainerElement) {
					buttonsContainerElement.style.display = 'none';
				}
			}
		}, 0);
	};

	onMount(() => {
		if (floatingButtons) {
			contentContainerElement?.addEventListener('mouseup', updateButtonPosition);
			document.addEventListener('mouseup', updateButtonPosition);
		}
	});

	onDestroy(() => {
		if (floatingButtons) {
			contentContainerElement?.removeEventListener('mouseup', updateButtonPosition);
			document.removeEventListener('mouseup', updateButtonPosition);
		}
	});
</script>

<div bind:this={contentContainerElement}>
	<Markdown
		{id}
		{content}
		{model}
		{save}
		on:update={(e) => {
			dispatch('update', e.detail);
		}}
		on:code={(e) => {
			const { lang, code } = e.detail;

			if (
				(['html', 'svg'].includes(lang) || (lang === 'xml' && code.includes('svg'))) &&
				!$mobile
			) {
				showArtifacts.set(true);
				showControls.set(true);
			}
		}}
	/>
</div>

{#if floatingButtons}
	<div
		bind:this={buttonsContainerElement}
		class="absolute rounded-lg mt-1 p-1 bg-white dark:bg-gray-850 text-xs text-medium shadow-lg"
		style="display: none"
	>
		<button
			class="px-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded flex items-center gap-0.5 min-w-fit"
			on:click={() => {
				const selection = window.getSelection();
				dispatch('explain', selection.toString());

				// Clear selection
				selection.removeAllRanges();
				buttonsContainerElement.style.display = 'none';
			}}
		>
			<LightBlub className="size-3 shrink-0" />

			<div class="shrink-0">Explain</div>
		</button>
	</div>
{/if}
