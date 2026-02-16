<script lang="ts">
	import dayjs from 'dayjs';
	import { DropdownMenu } from 'bits-ui';
	import { onMount, onDestroy, getContext, createEventDispatcher } from 'svelte';
	import { searchNotes } from '$lib/apis/notes';
	import { searchKnowledgeBases, searchKnowledgeFiles } from '$lib/apis/knowledge';

	import { flyAndScale } from '$lib/utils/transitions';
	import { decodeString } from '$lib/utils';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import PageEdit from '$lib/components/icons/PageEdit.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let onClose: Function = () => {};

	let show = false;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let noteItems = [];
	let knowledgeItems = [];
	let fileItems = [];

	let items = [];

	$: items = [...noteItems, ...knowledgeItems, ...fileItems];

	$: if (query !== undefined) {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			getItems();
		}, 300);
	}

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});

	const getItems = () => {
		getNoteItems();
		getKnowledgeItems();
		getKnowledgeFileItems();
	};

	const getNoteItems = async () => {
		const res = await searchNotes(localStorage.token, query).catch(() => {
			return null;
		});

		if (res) {
			noteItems = res.items.map((note) => {
				return {
					...note,
					type: 'note',
					name: note.title,
					description: dayjs(note.updated_at / 1000000).fromNow()
				};
			});
		}
	};

	const getKnowledgeItems = async () => {
		const res = await searchKnowledgeBases(localStorage.token, query).catch(() => {
			return null;
		});

		if (res) {
			knowledgeItems = res.items.map((note) => {
				return {
					...note,
					type: 'collection'
				};
			});
		}
	};

	const getKnowledgeFileItems = async () => {
		const res = await searchKnowledgeFiles(localStorage.token, query).catch(() => {
			return null;
		});

		if (res) {
			fileItems = res.items.map((file) => {
				return {
					...file,
					type: 'file',
					name: file.meta?.name || file.filename,
					description: file.description || ''
				};
			});
		}
	};

	onMount(async () => {
		getItems();
	});
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
			query = '';
		}
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu.Content
			class="z-[10000] text-black dark:text-white rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 w-70 p-1.5"
			sideOffset={8}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<div class=" flex w-full space-x-2 px-2 pb-0.5">
				<div class="flex flex-1">
					<div class=" self-center mr-2">
						<Search className="size-3.5" />
					</div>
					<input
						class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
						bind:value={query}
						placeholder={$i18n.t('Search')}
					/>
				</div>
			</div>

			<div class="max-h-56 overflow-y-scroll gap-0.5 flex flex-col">
				{#if items.length === 0}
					<div class="text-center text-xs text-gray-500 dark:text-gray-400 pt-4 pb-6">
						{$i18n.t('No knowledge found')}
					</div>
				{:else}
					{#each items as item, i}
						{#if i === 0 || item?.type !== items[i - 1]?.type}
							<div class="px-2 text-xs text-gray-500 py-1">
								{#if item?.type === 'note'}
									{$i18n.t('Notes')}
								{:else if item?.type === 'collection'}
									{$i18n.t('Collections')}
								{:else if item?.type === 'file'}
									{$i18n.t('Files')}
								{/if}
							</div>
						{/if}

						<div
							class=" px-2.5 py-1 rounded-xl w-full text-left flex justify-between items-center text-sm hover:bg-gray-50 hover:dark:bg-gray-800 hover:dark:text-gray-100 selected-command-option-button"
						>
							<button
								class="w-full flex-1"
								type="button"
								on:click={() => {
									dispatch('select', item);
									show = false;
								}}
							>
								<div class="  text-black dark:text-gray-100 flex items-center gap-1 shrink-0">
									{#if item.type === 'note'}
										<Tooltip
											content={$i18n.t('Note')}
											placement="top"
											tippyOptions={{ zIndex: 100000 }}
										>
											<PageEdit className="size-4" />
										</Tooltip>
									{:else if item.type === 'collection'}
										<Tooltip
											content={$i18n.t('Collection')}
											placement="top"
											tippyOptions={{ zIndex: 100000 }}
										>
											<Database className="size-4" />
										</Tooltip>
									{:else if item.type === 'file'}
										<Tooltip
											content={$i18n.t('File')}
											placement="top"
											tippyOptions={{ zIndex: 100000 }}
										>
											<DocumentPage className="size-4" />
										</Tooltip>
									{/if}

									<Tooltip
										content={item.description || decodeString(item?.name)}
										placement="top-start"
										tippyOptions={{ zIndex: 100000 }}
									>
										<div class="line-clamp-1 flex-1 text-sm text-left">
											{decodeString(item?.name)}
										</div>
									</Tooltip>
								</div>
							</button>
						</div>
					{/each}
				{/if}
			</div>
		</DropdownMenu.Content>
	</div>
</Dropdown>
