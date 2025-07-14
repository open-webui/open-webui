<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Fuse from 'fuse.js';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { tick, getContext, onMount, onDestroy } from 'svelte';
	import { removeLastWordFromString, isValidHttpUrl } from '$lib/utils';
	import { knowledge } from '$lib/stores';
	import { getNoteList, getNotes } from '$lib/apis/notes';

	const i18n = getContext('i18n');

	export let command = '';
	export let onSelect = (e) => {};

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

	const confirmSelect = async (type, data) => {
		onSelect({
			type: type,
			data: data
		});
	};

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};

	onMount(async () => {
		window.addEventListener('resize', adjustHeight);
		adjustHeight();

		let notes = await getNoteList(localStorage.token).catch(() => {
			return [];
		});

		notes = notes.map((note) => {
			return {
				...note,
				type: 'note',
				name: note.title,
				description: dayjs(note.updated_at / 1000000).fromNow()
			};
		});

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
											collection: { name: item.name, description: item.description } // DO NOT REMOVE, USED IN FILE DESCRIPTION/ATTACHMENT
										}))
									])
								];
							}, [])
							.map((file) => ({
								...file,
								name: file?.meta?.name,
								description: `${file?.collection?.name} - ${file?.collection?.description}`,
								knowledge: true, // DO NOT REMOVE, USED TO INDICATE KNOWLEDGE BASE FILE
								type: 'file'
							}))
					]
				: [];

		items = [
			...notes,
			...collections,
			...collection_files,
			...legacy_collections,
			...legacy_documents
		].map((item) => {
			return {
				...item,
				...(item?.legacy || item?.meta?.legacy || item?.meta?.document ? { legacy: true } : {})
			};
		});

		fuse = new Fuse(items, {
			keys: ['name', 'description']
		});
	});

	onDestroy(() => {
		window.removeEventListener('resize', adjustHeight);
	});
</script>

{#if filteredItems.length > 0 || command?.substring(1).startsWith('http')}
	<div
		id="commands-container"
		class="px-2 mb-2 text-left w-full absolute bottom-0 left-0 right-0 z-10"
	>
		<div class="flex w-full rounded-xl border border-gray-100 dark:border-gray-850">
			<div class="flex flex-col w-full rounded-xl bg-white dark:bg-gray-900 dark:text-gray-100">
				<div
					class="m-1 overflow-y-auto p-1 rounded-r-xl space-y-0.5 scrollbar-hidden max-h-60"
					id="command-options-container"
					bind:this={container}
				>
					{#each filteredItems as item, idx}
						<button
							class=" px-3 py-1.5 rounded-xl w-full text-left flex justify-between items-center {idx ===
							selectedIdx
								? ' bg-gray-50 dark:bg-gray-850 dark:text-gray-100 selected-command-option-button'
								: ''}"
							type="button"
							on:click={() => {
								console.log(item);
								confirmSelect('knowledge', item);
							}}
							on:mousemove={() => {
								selectedIdx = idx;
							}}
						>
							<div>
								<div class=" font-medium text-black dark:text-gray-100 flex items-center gap-1">
									{#if item.legacy}
										<div
											class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded-sm uppercase text-xs font-bold px-1 shrink-0"
										>
											Legacy
										</div>
									{:else if item?.meta?.document}
										<div
											class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded-sm uppercase text-xs font-bold px-1 shrink-0"
										>
											Document
										</div>
									{:else if item?.type === 'file'}
										<div
											class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded-sm uppercase text-xs font-bold px-1 shrink-0"
										>
											File
										</div>
									{:else if item?.type === 'note'}
										<div
											class="bg-blue-500/20 text-blue-700 dark:text-blue-200 rounded-sm uppercase text-xs font-bold px-1 shrink-0"
										>
											Note
										</div>
									{:else}
										<div
											class="bg-green-500/20 text-green-700 dark:text-green-200 rounded-sm uppercase text-xs font-bold px-1 shrink-0"
										>
											Collection
										</div>
									{/if}

									<div class="line-clamp-1">
										{decodeString(item?.name)}
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
														class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded-sm uppercase text-xs font-bold px-1 shrink-0"
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
										{$i18n.t('File not found.')}
									</div>
								{/if}
							</div> -->
					{/each}

					{#if command.substring(1).startsWith('https://www.youtube.com') || command
							.substring(1)
							.startsWith('https://youtu.be')}
						<button
							class="px-3 py-1.5 rounded-xl w-full text-left bg-gray-50 dark:bg-gray-850 dark:text-gray-100 selected-command-option-button"
							type="button"
							on:click={() => {
								if (isValidHttpUrl(command.substring(1))) {
									confirmSelect('youtube', command.substring(1));
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
								{command.substring(1)}
							</div>

							<div class=" text-xs text-gray-600 line-clamp-1">{$i18n.t('Youtube')}</div>
						</button>
					{:else if command.substring(1).startsWith('http')}
						<button
							class="px-3 py-1.5 rounded-xl w-full text-left bg-gray-50 dark:bg-gray-850 dark:text-gray-100 selected-command-option-button"
							type="button"
							on:click={() => {
								if (isValidHttpUrl(command.substring(1))) {
									confirmSelect('web', command.substring(1));
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
								{command}
							</div>

							<div class=" text-xs text-gray-600 line-clamp-1">{$i18n.t('Web')}</div>
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
