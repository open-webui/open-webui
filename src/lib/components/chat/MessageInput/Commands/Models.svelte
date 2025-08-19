<script lang="ts">
	import Fuse from 'fuse.js';

	import { createEventDispatcher, onDestroy, onMount } from 'svelte';
	import { tick, getContext } from 'svelte';

	import { models } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	export let command = '';
	export let onSelect = (e) => {};

	let selectedIdx = 0;
	let filteredItems = [];

	let fuse = new Fuse(
		$models
			.filter((model) => !model?.info?.meta?.hidden)
			.map((model) => {
				const _item = {
					...model,
					modelName: model?.name,
					tags: model?.info?.meta?.tags?.map((tag) => tag.name).join(' '),
					desc: model?.info?.meta?.description
				};
				return _item;
			}),
		{
			keys: ['value', 'tags', 'modelName'],
			threshold: 0.3
		}
	);

	$: filteredItems = command.slice(1)
		? fuse.search(command).map((e) => {
				return e.item;
			})
		: $models.filter((model) => !model?.info?.meta?.hidden);

	$: if (command) {
		selectedIdx = 0;
	}

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
	};

	let container;
	let adjustHeightDebounce;

	const adjustHeight = () => {
		if (container) {
			if (adjustHeightDebounce) {
				clearTimeout(adjustHeightDebounce);
			}

			adjustHeightDebounce = setTimeout(() => {
				if (!container) return;

				// Ensure the container is visible before adjusting height
				const rect = container.getBoundingClientRect();
				container.style.maxHeight = Math.max(Math.min(240, rect.bottom - 100), 100) + 'px';
			}, 100);
		}
	};

	const confirmSelect = async (model) => {
		onSelect({ type: 'model', data: model });
	};

	onMount(async () => {
		window.addEventListener('resize', adjustHeight);

		await tick();
		const chatInputElement = document.getElementById('chat-input');
		await tick();
		chatInputElement?.focus();
		await tick();

		adjustHeight();
	});

	onDestroy(() => {
		window.removeEventListener('resize', adjustHeight);
	});
</script>

{#if filteredItems.length > 0}
	<div
		id="commands-container"
		class="px-2 mb-2 text-left w-full absolute bottom-0 left-0 right-0 z-10"
	>
		<div class="flex w-full rounded-xl border border-gray-100 dark:border-gray-850">
			<div class="flex flex-col w-full rounded-xl bg-white dark:bg-gray-900 dark:text-gray-100">
				<div
					class="m-1 overflow-y-auto p-1 rounded-r-lg space-y-0.5 scrollbar-hidden max-h-60"
					id="command-options-container"
					bind:this={container}
				>
					{#each filteredItems as model, modelIdx}
						<button
							class="px-3 py-1.5 rounded-xl w-full text-left {modelIdx === selectedIdx
								? 'bg-gray-50 dark:bg-gray-850 selected-command-option-button'
								: ''}"
							type="button"
							on:click={() => {
								confirmSelect(model);
							}}
							on:mousemove={() => {
								selectedIdx = modelIdx;
							}}
							on:focus={() => {}}
						>
							<div class="flex font-medium text-black dark:text-gray-100 line-clamp-1">
								<img
									src={model?.info?.meta?.profile_image_url ??
										`${WEBUI_BASE_URL}/static/favicon.png`}
									alt={model?.name ?? model.id}
									class="rounded-full size-6 items-center mr-2"
								/>
								{model.name}
							</div>
						</button>
					{/each}
				</div>
			</div>
		</div>
	</div>
{/if}
