<script>
	import { onDestroy, onMount, tick, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Markdown from './Markdown.svelte';
	import LightBlub from '$lib/components/icons/LightBlub.svelte';
	import { mobile, showArtifacts, showControls, showOverview } from '$lib/stores';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';

	export let id;
	export let content;
	export let model = null;

	export let save = false;
	export let floatingButtons = true;

	let contentContainerElement;
	let buttonsContainerElement;

	let selectedText = '';
	let floatingInput = false;
	let floatingInputValue = '';

	const updateButtonPosition = (event) => {
		setTimeout(async () => {
			await tick();

			// Check if the event target is within the content container
			if (!contentContainerElement?.contains(event.target)) return;

			let selection = window.getSelection();

			if (selection.toString().trim().length > 0) {
				floatingInput = false;
				const range = selection.getRangeAt(0);
				const rect = range.getBoundingClientRect();

				// Calculate position relative to the viewport (now that it's in document.body)
				const top = rect.bottom + window.scrollY;
				const left = rect.left + window.scrollX;

				if (buttonsContainerElement) {
					buttonsContainerElement.style.display = 'block';
					buttonsContainerElement.style.left = `${left}px`;
					buttonsContainerElement.style.top = `${top + 5}px`; // +5 to add some spacing
				}
			} else {
				if (buttonsContainerElement) {
					buttonsContainerElement.style.display = 'none';
					selectedText = '';
					floatingInput = false;
					floatingInputValue = '';
				}
			}
		}, 0);
	};

	const selectAskHandler = () => {
		dispatch('select', {
			type: 'ask',
			content: selectedText,
			input: floatingInputValue
		});

		floatingInput = false;
		floatingInputValue = '';
		selectedText = '';

		// Clear selection
		window.getSelection().removeAllRanges();
		buttonsContainerElement.style.display = 'none';
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

	$: if (floatingButtons) {
		if (buttonsContainerElement) {
			document.body.appendChild(buttonsContainerElement);
		}
	}

	onDestroy(() => {
		if (buttonsContainerElement) {
			document.body.removeChild(buttonsContainerElement);
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
		class="absolute rounded-lg mt-1 text-xs z-[9999]"
		style="display: none"
	>
		{#if !floatingInput}
			<div
				class="flex flex-row gap-0.5 shrink-0 p-1 bg-white dark:bg-gray-850 dark:text-gray-100 text-medium shadow-xl"
			>
				<button
					class="px-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded flex items-center gap-1 min-w-fit"
					on:click={() => {
						selectedText = window.getSelection().toString();
						floatingInput = true;
					}}
				>
					<ChatBubble className="size-3 shrink-0" />

					<div class="shrink-0">Ask</div>
				</button>
				<button
					class="px-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded flex items-center gap-1 min-w-fit"
					on:click={() => {
						const selection = window.getSelection();
						dispatch('select', {
							type: 'explain',
							content: selection.toString()
						});

						// Clear selection
						selection.removeAllRanges();
						buttonsContainerElement.style.display = 'none';
					}}
				>
					<LightBlub className="size-3 shrink-0" />

					<div class="shrink-0">Explain</div>
				</button>
			</div>
		{:else}
			<div
				class="py-1 flex dark:text-gray-100 bg-gray-50 dark:bg-gray-800 border dark:border-gray-800 w-72 rounded-full shadow-xl"
			>
				<input
					type="text"
					class="ml-5 bg-transparent outline-none w-full flex-1 text-sm"
					placeholder={$i18n.t('Ask a question')}
					bind:value={floatingInputValue}
					on:keydown={(e) => {
						if (e.key === 'Enter') {
							selectAskHandler();
						}
					}}
				/>

				<div class="ml-1 mr-2">
					<button
						class="{floatingInputValue !== ''
							? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
							: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 m-0.5 self-center"
						on:click={() => {
							selectAskHandler();
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="size-4"
						>
							<path
								fill-rule="evenodd"
								d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
				</div>
			</div>
		{/if}
	</div>
{/if}
