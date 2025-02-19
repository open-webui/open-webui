<script lang="ts">
	import Fuse from 'fuse.js';

	import { createEventDispatcher, onMount } from 'svelte';
	import { tick, getContext } from 'svelte';

	import { models } from '$lib/stores';

	const i18n = getContext('i18n');

	const dispatch = createEventDispatcher();

	export let command = '';

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

	const confirmSelect = async (model) => {
		command = '';
		dispatch('select', model);
	};

	onMount(async () => {
		await tick();
		const chatInputElement = document.getElementById('chat-input');
		await tick();
		chatInputElement?.focus();
		await tick();
	});
</script>

{#if filteredItems.length > 0}
	<div
		id="commands-container"
		class="px-2 mb-2 text-left w-full absolute bottom-0 left-0 right-0 z-10"
	>
		<div class="flex w-full rounded-xl border border-gray-100 dark:border-gray-850">
			<div
				class="max-h-60 flex flex-col w-full rounded-xl bg-white dark:bg-gray-900 dark:text-gray-100"
			>
				<div class="m-1 overflow-y-auto p-1 rounded-r-lg space-y-0.5 scrollbar-hidden">
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
									src={model?.info?.meta?.profile_image_url ?? '/static/favicon.png'}
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
