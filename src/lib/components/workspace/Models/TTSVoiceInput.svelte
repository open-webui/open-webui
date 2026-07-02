<script lang="ts">
	import { createEventDispatcher, tick } from 'svelte';

	type Voice = {
		id: string;
		name?: string;
		description?: string;
		meta?: {
			description?: string;
		};
	};

	export let id = 'tts-voice';
	export let value = '';
	export let voices: Voice[] = [];
	export let placeholder = '';
	export let className = 'w-full';

	const dispatch = createEventDispatcher<{ select: Voice }>();
	const listboxId = `${id}-options`;

	let inputElement: HTMLInputElement | null = null;
	let popupElement: HTMLDivElement | null = null;
	let suggestionsOpen = false;

	$: query = value.trim().toLowerCase();
	$: filteredVoices = (voices ?? [])
		.filter((voice) => {
			const id = voice.id.toLowerCase();
			const name = (voice.name ?? '').toLowerCase();
			const description = (voice.description ?? voice.meta?.description ?? '').toLowerCase();

			return (
				query === '' || id.includes(query) || name.includes(query) || description.includes(query)
			);
		})
		.slice(0, 8);
	$: if (suggestionsOpen && filteredVoices.length > 0) {
		tick().then(positionPopup);
	}

	const portal = (node: HTMLElement) => {
		document.body.appendChild(node);
		return {
			destroy() {
				node.remove();
			}
		};
	};

	const positionPopup = () => {
		if (!inputElement || !popupElement) return;

		const rect = inputElement.getBoundingClientRect();
		const width = Math.min(192, rect.width, window.innerWidth - 16);

		popupElement.style.top = `${rect.bottom + 4}px`;
		popupElement.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - width - 8))}px`;
		popupElement.style.width = `${width}px`;
	};

	const selectVoice = (voice: Voice) => {
		value = voice.id;
		suggestionsOpen = false;
		dispatch('select', voice);
	};

	const handlePointerDown = (event: PointerEvent) => {
		if (!suggestionsOpen) return;

		const target = event.target as Node;
		if (inputElement?.contains(target) || popupElement?.contains(target)) {
			return;
		}

		suggestionsOpen = false;
	};
</script>

<svelte:window
	on:pointerdown={handlePointerDown}
	on:scroll|capture={positionPopup}
	on:resize={positionPopup}
/>

<input
	bind:this={inputElement}
	bind:value
	id={`${id}-input`}
	class="{className} text-sm bg-transparent outline-hidden"
	type="text"
	{placeholder}
	role="combobox"
	aria-autocomplete="list"
	aria-controls={listboxId}
	aria-expanded={suggestionsOpen && filteredVoices.length > 0}
	autocomplete="off"
	on:focus={() => {
		suggestionsOpen = true;
		positionPopup();
	}}
	on:input={() => {
		suggestionsOpen = true;
		positionPopup();
	}}
	on:keydown={(event) => {
		if (event.key === 'Escape') {
			suggestionsOpen = false;
		}
	}}
	on:blur={() => {
		setTimeout(() => {
			if (!popupElement?.contains(document.activeElement)) {
				suggestionsOpen = false;
			}
		}, 0);
	}}
/>

{#if suggestionsOpen && filteredVoices.length > 0}
	<div
		use:portal
		bind:this={popupElement}
		id={listboxId}
		class="fixed max-h-48 overflow-y-auto rounded-2xl border border-gray-200 bg-white p-0.5 shadow-lg dark:border-gray-800 dark:bg-gray-850"
		role="listbox"
		style="z-index: 9999; top: 0; left: 0;"
	>
		{#each filteredVoices as voice (voice.id)}
			<button
				type="button"
				class="flex w-full items-center justify-between gap-3 rounded-xl px-2 py-[5px] text-left text-xs text-gray-700 transition-colors hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-800"
				role="option"
				aria-selected={value === voice.id}
				on:mousedown={(event) => {
					event.preventDefault();
				}}
				on:click={() => {
					selectVoice(voice);
				}}
			>
				<span class="truncate">{voice.id}</span>
				{#if voice.name && voice.name !== voice.id}
					<span class="truncate text-gray-500 dark:text-gray-400">{voice.name}</span>
				{/if}
			</button>
		{/each}
	</div>
{/if}
