<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Fuse from 'fuse.js';

	import { createEventDispatcher, tick, getContext, onMount } from 'svelte';
	import { removeLastWordFromString, isValidHttpUrl } from '$lib/utils';
	import { knowledge } from '$lib/stores';

	const i18n = getContext('i18n');

	export let prompt = '';
	export let command = '';

	const dispatch = createEventDispatcher();
	let selectedIdx = 0;

	let items = [];
	let fuse = null;

	let filteredItems = [];
	$: if (fuse) {
		filteredItems = command.slice(1)
			? fuse.search(command).map((e) => {
					return e.item;
				})
			: items;
	}

	$: if (command) {
		selectedIdx = 0;
	}

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
	};

	const confirmSelect = async (item) => {
		dispatch('select', item);

		prompt = removeLastWordFromString(prompt, command);
		const chatInputElement = document.getElementById('chat-textarea');

		await tick();
		chatInputElement?.focus();
		await tick();
	};

	const confirmSelectWeb = async (url) => {
		dispatch('url', url);

		prompt = removeLastWordFromString(prompt, command);
		const chatInputElement = document.getElementById('chat-textarea');

		await tick();
		chatInputElement?.focus();
		await tick();
	};

	const confirmSelectYoutube = async (url) => {
		dispatch('youtube', url);

		prompt = removeLastWordFromString(prompt, command);
		const chatInputElement = document.getElementById('chat-textarea');

		await tick();
		chatInputElement?.focus();
		await tick();
	};

	onMount(() => {
		let legacy_documents = $knowledge.filter((item) => item?.meta?.document);
		let legacy_collections =
			legacy_documents.length > 0
				? [
						{
							name: 'All Documents',
							legacy: true,
							type: 'collection',
							description: 'Deprecated (legacy collection), please create a new knowledge base.',
							title: $i18n.t('All Documents'),
							collection_names: legacy_documents.map((item) => item.id)
						},

						...legacy_documents
							.reduce((a, item) => {
								return [...new Set([...a, ...(item?.meta?.tags ?? []).map((tag) => tag.name)])];
							}, [])
							.map((tag) => ({
								name: tag,
								legacy: true,
								type: 'collection',
								description: 'Deprecated (legacy collection), please create a new knowledge base.',
								collection_names: legacy_documents
									.filter((item) => (item?.meta?.tags ?? []).map((tag) => tag.name).includes(tag))
									.map((item) => item.id)
							}))
					]
				: [];

		items = [...$knowledge, ...legacy_collections].map((item) => {
			return {
				...item,
				...(item?.legacy || item?.meta?.legacy || item?.meta?.document ? { legacy: true } : {})
			};
		});

		fuse = new Fuse(items, {
			keys: ['name', 'description']
		});
	});
</script>

{#if filteredItems.length > 0 || prompt.split(' ')?.at(0)?.substring(1).startsWith('http')}
	<div
		id="commands-container"
		class="pl-2 pr-14 mb-3 text-left w-full absolute bottom-0 left-0 right-0 z-10"
	>
		<div class="flex w-full dark:border dark:border-gray-850 rounded-lg">
			<div class=" bg-gray-50 dark:bg-gray-850 w-10 rounded-l-lg text-center">
				<div class=" text-lg font-medium mt-2">#</div>
			</div>

			<div
				class="max-h-60 flex flex-col w-full rounded-r-xl bg-white dark:bg-gray-900 dark:text-gray-100"
			>
				<div class="m-1 overflow-y-auto p-1 rounded-r-xl space-y-0.5 scrollbar-hidden">
					{#each filteredItems as item, idx}
						<button
							class=" px-3 py-1.5 rounded-xl w-full text-left {idx === selectedIdx
								? ' bg-gray-50 dark:bg-gray-850 dark:text-gray-100 selected-command-option-button'
								: ''}"
							type="button"
							on:click={() => {
								console.log(item);
								confirmSelect(item);
							}}
							on:mousemove={() => {
								selectedIdx = idx;
							}}
							on:focus={() => {}}
						>
							<div class=" font-medium text-black dark:text-gray-100 flex items-center gap-1">
								{#if item.legacy}
									<div
										class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded uppercase text-xs font-bold px-1"
									>
										Legacy
									</div>
								{:else if item?.meta?.document}
									<div
										class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded uppercase text-xs font-bold px-1"
									>
										Document
									</div>
								{:else}
									<div
										class="bg-green-500/20 text-green-700 dark:text-green-200 rounded uppercase text-xs font-bold px-1"
									>
										Collection
									</div>
								{/if}

								<div class="line-clamp-1">
									{item.name}
								</div>
							</div>

							<div class=" text-xs text-gray-600 dark:text-gray-100 line-clamp-1">
								{item?.description}
							</div>
						</button>
					{/each}

					{#if prompt
						.split(' ')
						.some((s) => s.substring(1).startsWith('https://www.youtube.com') || s
									.substring(1)
									.startsWith('https://youtu.be'))}
						<button
							class="px-3 py-1.5 rounded-xl w-full text-left bg-gray-50 dark:bg-gray-850 dark:text-gray-100 selected-command-option-button"
							type="button"
							on:click={() => {
								const url = prompt.split(' ')?.at(0)?.substring(1);
								if (isValidHttpUrl(url)) {
									confirmSelectYoutube(url);
								} else {
									toast.error(
										$i18n.t(
											'Oops! Looks like the URL is invalid. Please double-check and try again.'
										)
									);
								}
							}}
						>
							<div class=" font-medium text-black dark:text-gray-100 line-clamp-1">
								{prompt.split(' ')?.at(0)?.substring(1)}
							</div>

							<div class=" text-xs text-gray-600 line-clamp-1">{$i18n.t('Youtube')}</div>
						</button>
					{:else if prompt.split(' ')?.at(0)?.substring(1).startsWith('http')}
						<button
							class="px-3 py-1.5 rounded-xl w-full text-left bg-gray-50 dark:bg-gray-850 dark:text-gray-100 selected-command-option-button"
							type="button"
							on:click={() => {
								const url = prompt.split(' ')?.at(0)?.substring(1);
								if (isValidHttpUrl(url)) {
									confirmSelectWeb(url);
								} else {
									toast.error(
										$i18n.t(
											'Oops! Looks like the URL is invalid. Please double-check and try again.'
										)
									);
								}
							}}
						>
							<div class=" font-medium text-black dark:text-gray-100 line-clamp-1">
								{prompt.split(' ')?.at(0)?.substring(1)}
							</div>

							<div class=" text-xs text-gray-600 line-clamp-1">{$i18n.t('Web')}</div>
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
