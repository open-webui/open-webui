<script lang="ts">
	import { getContext } from 'svelte';
	import { fly } from 'svelte/transition';

	import { decodeString } from '$lib/utils';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Hashtag from '$lib/components/icons/Hashtag.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	const i18n = getContext('i18n');

	export let target_type: 'chat' | 'channel' = 'chat';
	export let channel_id = '';
	export let folder_id = '';
	export let folders: any[] = [];
	export let channels: any[] = [];
	export let side: 'top' | 'bottom' = 'top';
	export let align: 'start' | 'end' = 'start';
	export let onChange: () => void = () => {};

	let show = false;
	let tab: '' | 'folders' | 'channels' = '';
	let folderSearch = '';
	let channelSearch = '';

	const folderName = (folder: any) => decodeString(folder?.name ?? $i18n.t('Folder'));
	const channelName = (channel: any) => channel?.name || $i18n.t('Channel');

	$: folderOptions = [...((folders ?? []) as any[])]
		.filter((folder) => folder?.id && !folder?.shared)
		.sort((a, b) => folderName(a).localeCompare(folderName(b)));
	$: folderById = new Map(folderOptions.map((folder) => [folder.id, folder]));
	$: channelOptions = (channels ?? [])
		.filter((channel) => channel?.id && channel.type !== 'dm')
		.sort((a, b) => channelName(a).localeCompare(channelName(b)));
	$: selectedFolder = folderOptions.find((folder) => folder.id === folder_id);
	$: selectedChannel = channelOptions.find((channel) => channel.id === channel_id);

	const folderPath = (folder: any) => {
		const names: string[] = [];
		const seen = new Set<string>();
		let current = folder;

		while (current?.parent_id && !seen.has(current.parent_id)) {
			seen.add(current.parent_id);
			const parent = folderById.get(current.parent_id);
			if (!parent) break;
			names.unshift(folderName(parent));
			current = parent;
		}

		return names.join(' / ');
	};

	$: destinationLabel =
		target_type === 'channel'
			? selectedChannel
				? `#${channelName(selectedChannel)}`
				: $i18n.t('Choose channel')
			: selectedFolder
				? folderName(selectedFolder)
				: $i18n.t('New chat');
	$: normalizedFolderSearch = folderSearch.trim().toLowerCase();
	$: filteredFolderOptions = normalizedFolderSearch
		? folderOptions.filter((folder) =>
				`${folderName(folder)} ${folderPath(folder)}`.toLowerCase().includes(normalizedFolderSearch)
			)
		: folderOptions;
	$: normalizedChannelSearch = channelSearch.trim().toLowerCase();
	$: filteredChannelOptions = normalizedChannelSearch
		? channelOptions.filter((channel) =>
				channelName(channel).toLowerCase().includes(normalizedChannelSearch)
			)
		: channelOptions;

	const selectChat = () => {
		target_type = 'chat';
		channel_id = '';
		folder_id = '';
		show = false;
		tab = '';
		onChange();
	};

	const selectFolder = (id: string) => {
		target_type = 'chat';
		channel_id = '';
		folder_id = id;
		show = false;
		tab = '';
		folderSearch = '';
		onChange();
	};

	const selectChannel = (id: string) => {
		target_type = 'channel';
		channel_id = id;
		folder_id = '';
		show = false;
		tab = '';
		channelSearch = '';
		onChange();
	};
</script>

<Dropdown
	bind:show
	{side}
	{align}
	onOpenChange={(state) => {
		if (!state) {
			tab = '';
			folderSearch = '';
			channelSearch = '';
		}
	}}
>
	<button
		type="button"
		class="relative h-8 max-w-[11rem] flex items-center gap-1.5 px-2.5 py-1.5 bg-transparent rounded-2xl text-xs font-normal text-gray-600 transition hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
	>
		{#if target_type === 'channel'}
			<Hashtag className="size-3.5 shrink-0" />
		{:else if folder_id}
			<Folder className="size-3.5 shrink-0" />
		{:else}
			<ChatBubble className="size-3.5 shrink-0" />
		{/if}
		<span class="min-w-0 truncate">{destinationLabel}</span>
		<ChevronDown className="size-2.5 shrink-0" strokeWidth="2.5" />
	</button>

	<div slot="content">
		<DropdownMenu className="w-72 max-h-72 overflow-hidden shadow-lg">
			{#if tab === ''}
				<div
					class="max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
					in:fly={{ x: -20, duration: 150 }}
				>
					<button
						type="button"
						class="flex h-[1.6875rem] w-full cursor-pointer items-center justify-between gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 {target_type ===
							'chat' && !folder_id
							? 'text-gray-900 dark:text-gray-100'
							: 'text-gray-700 dark:text-gray-300'}"
						on:click={selectChat}
					>
						<div class="flex min-w-0 items-center gap-1.5">
							<ChatBubble className="size-3.5 shrink-0" />
							<span class="min-w-0 truncate">{$i18n.t('New chat')}</span>
						</div>
						{#if target_type === 'chat' && !folder_id}
							<Check className="size-3.5 shrink-0" strokeWidth="2" />
						{/if}
					</button>

					<button
						type="button"
						class="flex h-[1.6875rem] w-full cursor-pointer items-center justify-between gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 {target_type ===
							'chat' && folder_id
							? 'text-gray-900 dark:text-gray-100'
							: 'text-gray-700 dark:text-gray-300'}"
						on:click={() => (tab = 'folders')}
					>
						<div class="flex min-w-0 items-center gap-1.5">
							<Folder className="size-3.5 shrink-0" />
							<span class="min-w-0 truncate">
								{selectedFolder ? folderName(selectedFolder) : $i18n.t('Folder')}
							</span>
						</div>
						<div class="flex shrink-0 items-center gap-1 text-gray-500">
							{#if target_type === 'chat' && folder_id}
								<Check className="size-3.5" strokeWidth="2" />
							{/if}
							<ChevronRight />
						</div>
					</button>

					<button
						type="button"
						class="flex h-[1.6875rem] w-full cursor-pointer items-center justify-between gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 {target_type ===
						'channel'
							? 'text-gray-900 dark:text-gray-100'
							: 'text-gray-700 dark:text-gray-300'}"
						on:click={() => (tab = 'channels')}
					>
						<div class="flex min-w-0 items-center gap-1.5">
							<Hashtag className="size-3.5 shrink-0" />
							<span class="min-w-0 truncate">
								{selectedChannel ? channelName(selectedChannel) : $i18n.t('Channel')}
							</span>
						</div>
						<div class="flex shrink-0 items-center gap-1 text-gray-500">
							{#if target_type === 'channel'}
								<Check className="size-3.5" strokeWidth="2" />
							{/if}
							<ChevronRight />
						</div>
					</button>
				</div>
			{:else if tab === 'folders'}
				<div class="flex max-h-72 flex-col overflow-hidden" in:fly={{ x: 20, duration: 150 }}>
					<button
						type="button"
						class="flex h-[1.6875rem] w-full shrink-0 cursor-pointer items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
						on:click={() => (tab = '')}
					>
						<ChevronLeft />
						<span>{$i18n.t('Folders')}</span>
					</button>

					<div class="flex shrink-0 items-center gap-1.5 px-2 py-1">
						<Search className="size-3.5 shrink-0" strokeWidth="2.5" />
						<input
							bind:value={folderSearch}
							class="w-full bg-transparent text-[0.8125rem] outline-hidden"
							placeholder={$i18n.t('Search folders')}
							autocomplete="off"
							on:click|stopPropagation
						/>
					</div>

					<div class="overflow-y-auto scrollbar-thin">
						{#each filteredFolderOptions as folder (folder.id)}
							{@const path = folderPath(folder)}
							<button
								type="button"
								class="flex h-[1.6875rem] w-full cursor-pointer items-center justify-between gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 {target_type ===
									'chat' && folder_id === folder.id
									? 'text-gray-900 dark:text-gray-100'
									: 'text-gray-700 dark:text-gray-300'}"
								title={path ? `${path} / ${folderName(folder)}` : folderName(folder)}
								on:click={() => selectFolder(folder.id)}
							>
								<div class="flex min-w-0 items-center gap-1.5">
									<Folder className="size-3.5 shrink-0" />
									<span class="min-w-0 truncate">{folderName(folder)}</span>
									{#if path}
										<span
											class="min-w-0 truncate text-[0.6875rem] text-gray-400 dark:text-gray-500"
										>
											{path}
										</span>
									{/if}
								</div>
								{#if target_type === 'chat' && folder_id === folder.id}
									<Check className="size-3.5 shrink-0" strokeWidth="2" />
								{/if}
							</button>
						{:else}
							<div class="px-2 py-1 text-[0.6875rem] text-gray-500 dark:text-gray-400">
								{folderOptions.length > 0 ? $i18n.t('No results found') : $i18n.t('No folders')}
							</div>
						{/each}
					</div>
				</div>
			{:else if tab === 'channels'}
				<div class="flex max-h-72 flex-col overflow-hidden" in:fly={{ x: 20, duration: 150 }}>
					<button
						type="button"
						class="flex h-[1.6875rem] w-full shrink-0 cursor-pointer items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
						on:click={() => (tab = '')}
					>
						<ChevronLeft />
						<span>{$i18n.t('Channels')}</span>
					</button>

					<div class="flex shrink-0 items-center gap-1.5 px-2 py-1">
						<Search className="size-3.5 shrink-0" strokeWidth="2.5" />
						<input
							bind:value={channelSearch}
							class="w-full bg-transparent text-[0.8125rem] outline-hidden"
							placeholder={$i18n.t('Search channels')}
							autocomplete="off"
							on:click|stopPropagation
						/>
					</div>

					<div class="overflow-y-auto scrollbar-thin">
						{#each filteredChannelOptions as channel (channel.id)}
							<button
								type="button"
								class="flex h-[1.6875rem] w-full cursor-pointer items-center justify-between gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 {target_type ===
									'channel' && channel_id === channel.id
									? 'text-gray-900 dark:text-gray-100'
									: 'text-gray-700 dark:text-gray-300'}"
								on:click={() => selectChannel(channel.id)}
							>
								<div class="flex min-w-0 items-center gap-1.5">
									<Hashtag className="size-3.5 shrink-0" />
									<span class="min-w-0 truncate">{channelName(channel)}</span>
								</div>
								{#if target_type === 'channel' && channel_id === channel.id}
									<Check className="size-3.5 shrink-0" strokeWidth="2" />
								{/if}
							</button>
						{:else}
							<div class="px-2 py-1 text-[0.6875rem] text-gray-500 dark:text-gray-400">
								{channelOptions.length > 0 ? $i18n.t('No results found') : $i18n.t('No channels')}
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</DropdownMenu>
	</div>
</Dropdown>
