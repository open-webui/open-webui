<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Fuse from 'fuse.js';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

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
		const chatInputElement = document.getElementById('chat-input');

		await tick();
		chatInputElement?.focus();
		await tick();
	};

	const confirmSelectWeb = async (url) => {
		dispatch('url', url);

		prompt = removeLastWordFromString(prompt, command);
		const chatInputElement = document.getElementById('chat-input');

		await tick();
		chatInputElement?.focus();
		await tick();
	};

	const confirmSelectYoutube = async (url) => {
		dispatch('youtube', url);

		prompt = removeLastWordFromString(prompt, command);
		const chatInputElement = document.getElementById('chat-input');

		await tick();
		chatInputElement?.focus();
		await tick();
	};

	onMount(() => {
		let legacy_documents = $knowledge
			.filter((item) => item?.meta?.document)
			.map((item) => ({
				...item,
				type: 'file'
			}));

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

		let collections = $knowledge
			.filter((item) => !item?.meta?.document)
			.map((item) => ({
				...item,
				type: 'collection'
			}));
		let collection_files =
			$knowledge.length > 0
				? [
						...$knowledge
							.reduce((a, item) => {
								return [
									...new Set([
										...a,
										...(item?.files ?? []).map((file) => ({
											...file,
											collection: { name: item.name, description: item.description }
										}))
									])
								];
							}, [])
							.map((file) => ({
								...file,
								name: file?.meta?.name,
								description: `${file?.collection?.name} - ${file?.collection?.description}`,
								type: 'file'
							}))
					]
				: [];

		items = [...collections, ...collection_files, ...legacy_collections, ...legacy_documents].map(
			(item) => {
				return {
					...item,
					...(item?.legacy || item?.meta?.legacy || item?.meta?.document ? { legacy: true } : {})
				};
			}
		);

		fuse = new Fuse(items, {
			keys: ['name', 'description']
		});
	});
</script>

{#if filteredItems.length > 0 || prompt.split(' ')?.at(0)?.substring(1).startsWith('http')}
	<div
		id="commands-container"
		class="px-2 mb-2 text-left w-full absolute bottom-0 left-0 right-0 z-10"
	>
		<div class="flex w-full rounded-xl border border-gray-50 dark:border-gray-850">
			<div
				class="max-h-60 flex flex-col w-full rounded-xl bg-white dark:bg-gray-900 dark:text-gray-100"
			>
				<div class="m-1 overflow-y-auto p-1 rounded-r-xl space-y-0.5 scrollbar-hidden">
					{#each filteredItems as item, idx}
						<button
							class=" px-3 py-1.5 rounded-xl w-full text-left flex justify-between items-center {idx ===
							selectedIdx
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
						>
							<div>
								<div class=" font-medium text-black dark:text-gray-100 flex items-center gap-1">
									{#if item.legacy}
										<div
											class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded uppercase text-xs font-bold px-1 flex-shrink-0"
										>
											Legacy
										</div>
									{:else if item?.meta?.document}
										<div
											class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded uppercase text-xs font-bold px-1 flex-shrink-0"
										>
											Document
										</div>
									{:else if item?.type === 'file'}
										<div
											class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded uppercase text-xs font-bold px-1 flex-shrink-0"
										>
											File
										</div>
									{:else}
										<div
											class="bg-green-500/20 text-green-700 dark:text-green-200 rounded uppercase text-xs font-bold px-1 flex-shrink-0"
										>
											Collection
										</div>
									{/if}

									<div class="line-clamp-1">
										{item?.name}
									</div>
								</div>

								<div class=" text-xs text-gray-600 dark:text-gray-100 line-clamp-1">
									{item?.description}
								</div>
							</div>
						</button>

						<!-- <div slot="content" class=" pl-2 pt-1 flex flex-col gap-0.5">
								{#if !item.legacy && (item?.files ?? []).length > 0}
									{#each item?.files ?? [] as file, fileIdx}
										<button
											class=" px-3 py-1.5 rounded-xl w-full text-left flex justify-between items-center hover:bg-gray-50 dark:hover:bg-gray-850 dark:hover:text-gray-100 selected-command-option-button"
											type="button"
											on:click={() => {
												console.log(file);
											}}
											on:mousemove={() => {
												selectedIdx = idx;
											}}
										>
											<div>
												<div
													class=" font-medium text-black dark:text-gray-100 flex items-center gap-1"
												>
													<div
														class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded uppercase text-xs font-bold px-1 flex-shrink-0"
													>
														File
													</div>

													<div class="line-clamp-1">
														{file?.meta?.name}
													</div>
												</div>

												<div class=" text-xs text-gray-600 dark:text-gray-100 line-clamp-1">
													{$i18n.t('Updated')}
													{dayjs(file.updated_at * 1000).fromNow()}
												</div>
											</div>
										</button>
									{/each}
								{:else}
									<div class=" text-gray-500 text-xs mt-1 mb-2">
										{$i18n.t('No files found.')}
									</div>
								{/if}
							</div> -->
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
