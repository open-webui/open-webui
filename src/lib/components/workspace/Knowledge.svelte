<script lang="ts">
	import Fuse from 'fuse.js';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, knowledge, showSidebar } from '$lib/stores';
	import {
		getKnowledgeBases,
		deleteKnowledgeById,
		getKnowledgeBaseList
	} from '$lib/apis/knowledge';

	import { goto } from '$app/navigation';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import ItemMenu from './Knowledge/ItemMenu.svelte';
	import Badge from '../common/Badge.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { capitalizeFirstLetter } from '$lib/utils';
	import Tooltip from '../common/Tooltip.svelte';
	import ShowSidebarIcon from '../icons/ShowSidebarIcon.svelte';
	import GroupIcon from '../icons/GroupIcon.svelte';
	import PublicIcon from '../icons/PublicIcon.svelte';
	import PrivateIcon from '../icons/PrivateIcon.svelte';
	import { getGroups } from '$lib/apis/groups';
	import { user } from '$lib/stores';

	let loaded = false;

	let query = '';
	let selectedItem = null;
	let showDeleteConfirm = false;

	let fuse = null;

	let knowledgeBases = [];
	let filteredItems = [];

	$: if (knowledgeBases) {
		fuse = new Fuse(knowledgeBases, {
			keys: ['name', 'description']
		});
	}

	let showInput = false;

	let accessFilter = 'all';
	let groupsForKnowledge;

	$: if (fuse) {
	let result = query
		? fuse.search(query).map((e) => e.item)
		: knowledgeBases;

	filteredItems = result.filter((m) => {
		const isPublic = m.access_control === null;
		const isPrivate = m.access_control !== null;

		const accessMatch =
			accessFilter === 'all' ||
			(accessFilter === 'public' && isPublic) ||
			(accessFilter === 'private' && isPrivate);

		return accessMatch;
	});
}

	const deleteHandler = async (item) => {
		const res = await deleteKnowledgeById(localStorage.token, item.id).catch((e) => {
			toast.error(`${e}`);
		});

		if (res) {
			knowledgeBases = await getKnowledgeBaseList(localStorage.token);
			knowledge.set(await getKnowledgeBases(localStorage.token));
			toast.success($i18n.t('Knowledge deleted successfully.'));
		}
	};

	function getGroupNamesFromAccess(model) {
		if (!model.access_control) return [];

		const readGroups = model.access_control.read?.group_ids || [];
		const writeGroups = model.access_control.write?.group_ids || [];

		const allGroupIds = Array.from(new Set([...readGroups, ...writeGroups]));

		const matchedGroups = allGroupIds
			.map((id) => groupsForKnowledge.find((g) => g.id === id))
			.filter(Boolean)
			.map((g) => g.name);

		return matchedGroups;
	}

	onMount(async () => {
		knowledgeBases = await getKnowledgeBaseList(localStorage.token);
		let groups = await getGroups(localStorage.token);
		groupsForKnowledge = groups;
		loaded = true;
	});
	
	let scrollContainer;

	function updateScrollHeight() {
		const header = document.getElementById('assistants-header');
		const filters = document.getElementById('assistants-filters');

		if (header && filters && scrollContainer) {
			const totalOffset = header.offsetHeight + filters.offsetHeight;
			scrollContainer.style.height = `calc(100dvh - ${totalOffset}px)`;
		}
	}

	onMount(() => {
		window.addEventListener('resize', updateScrollHeight);
		return () => {
			window.removeEventListener('resize', updateScrollHeight);
		};
	});

	let hoveredKowledge = null;
	let menuIdOpened = null;
</script>

<svelte:head>
	<title>
		{$i18n.t('Knowledge')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		on:confirm={() => {
			deleteHandler(selectedItem);
		}}
	/>

	<div id="knowledge-header" class="pl-[22px] pr-[15px] py-2.5 border-b dark:border-customGray-700">
		<div class="flex justify-between items-center">
			<div class="{$showSidebar ? 'md:hidden' : ''} self-center flex flex-none items-center">
				<button
					id="sidebar-toggle-button"
					class="cursor-pointer p-1.5 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={() => {
						showSidebar.set(!$showSidebar);
					}}
					aria-label="Toggle Sidebar"
				>
					<div class=" m-auto self-center">
						<ShowSidebarIcon />
					</div>
				</button>
			</div>
			<div class="flex items-center md:self-center text-lightGray-100 dark:bg-customGray-100 text-base font-medium leading-none px-0.5">
				{$i18n.t('Knowledge')}
			</div>
			<div class="flex">
				<div
					class="flex flex-1 items-center p-2.5 rounded-lg mr-1 border border-lightGray-400 dark:border-customGray-700 hover:bg-lightGray-700 dark:hover:bg-customGray-950 dark:hover:text-white transition"
				>
					<button
						class=""
						on:click={() => {
							showInput = !showInput;
							if (!showInput) query = '';
						}}
						aria-label="Toggle Search"
					>
						<Search className="size-3.5" />
					</button>
					<!-- </div> -->
					{#if showInput}
						<input
							class=" w-full text-xs outline-none bg-transparent leading-none pl-2 text-lightGray-100 dark:text-customGray-100"
							bind:value={query}
							placeholder={$i18n.t('Search Models')}
							autofocus
							on:blur={() => {
								if (query.trim() === '') showInput = false;
							}}
						/>
					{/if}
				</div>
				<div>
					<a
						class=" px-2 py-2.5 w-[35px] sm:w-[220px] rounded-lg leading-none border border-lightGray-400 dark:border-customGray-700 hover:bg-lightGray-700 dark:hover:bg-customGray-950 text-lightGray-100 dark:text-customGray-200 dark:hover:text-white transition font-medium text-xs flex items-center justify-center space-x-1"
						href="/workspace/knowledge/create"
					>
						<Plus className="size-3.5" />
						<span class="hidden sm:block">{$i18n.t('Create new')}</span>
					</a>
				</div>
			</div>
		</div>
	</div>
	<div class="pl-[22px] pr-[15px]">
		<div
			id="knowledge-filters"
			class="flex items-center justify-end py-5 pr-[22px] flex-col md:flex-row"
		>
			<div class="flex bg-lightGray-700 dark:bg-customGray-800 rounded-md flex-shrink-0">
				<button
					on:click={() => (accessFilter = 'all')}
					class={`${accessFilter === 'all' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-[23px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('All')}</button
				>
				<button
					on:click={() => (accessFilter = 'private')}
					class={`${accessFilter === 'private' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-[23px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('Private')}</button
				>
				<button
					on:click={() => (accessFilter = 'public')}
					class={`${accessFilter === 'public' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-[23px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('Public')}</button
				>
			</div>
		</div>
		<div
			id="knowledge-scroll-container"
			bind:this={scrollContainer}
			class="overflow-y-scroll pr-[3px]"
		>	
			{#if knowledgeBases?.length < 1}
				<div class="flex h-[calc(100dvh-200px)] w-full justify-center items-center">
					<div class="text-sm dark:text-customGray-100/50">{$i18n.t('No knowledge added yet')}</div>
				</div>
			{/if}
			<div class="mb-2 gap-2 grid lg:grid-cols-2 xl:grid-cols-3" id="knowledge-list">
				{#each filteredItems as item}
					<button
					on:mouseenter={() =>  hoveredKowledge = item.id}
					on:mouseleave={() =>  hoveredKowledge = null}
						class="group flex flex-col gap-y-1 cursor-pointer w-full px-3 py-2 bg-lightGray-550 dark:bg-customGray-800 rounded-2xl transition"
						on:click={() => {
							if (item?.meta?.document) {
								toast.error(
									$i18n.t(
										'Only collections can be edited, create a new knowledge base to edit/add documents.'
									)
								);
							} else {
								if($user.id === item.user_id || $user?.role === 'admin')
								goto(`/workspace/knowledge/${item.id}`);
							}
						}}
					>
						<div class=" w-full">
							<div class="flex items-start justify-between">
								<div class="flex items-center">
									<div class="flex items-center gap-1 flex-wrap">
										{#if item.access_control == null}
											<div
												class="flex gap-1 items-center text-xs dark:bg-customGray-900 px-[6px] py-[3px] rounded-md bg-lightGray-400 font-medium {(hoveredKowledge === item.id || menuIdOpened === item.id) ? 'dark:text-white' : 'text-lightGray-100 dark:text-customGray-300'}"
											>
												<PublicIcon />
												<span>{$i18n.t('Public')}</span>
											</div>
										{:else if getGroupNamesFromAccess(item).length < 1}
											<div
												class="flex gap-1 items-center text-xs dark:bg-customGray-900 px-[6px] py-[3px] rounded-md bg-lightGray-400 font-medium {(hoveredKowledge === item.id || menuIdOpened === item.id) ? 'dark:text-white' : 'text-lightGray-100 dark:text-customGray-300'}"
											>
												<PrivateIcon />
												<span>{$i18n.t('Private')}</span>
											</div>
										{:else}
											{#each getGroupNamesFromAccess(item) as groupName}
												<div
													class="flex items-center text-xs dark:bg-customGray-900 px-[6px] py-[3px] rounded-md bg-lightGray-400 font-medium {(hoveredKowledge === item.id || menuIdOpened === item.id) ? 'dark:text-white' : 'text-lightGray-100 dark:text-customGray-300'}"
												>
													<GroupIcon />
													<span>{groupName}</span>
												</div>
											{/each}
										{/if}
									</div>
								</div>
								{#if ($user.id === item.user_id || $user?.role === 'admin')}
								<div class="{(hoveredKowledge === item.id || menuIdOpened === item.id) ? 'visible' : 'invisible'}">
									<ItemMenu
										{item}
										on:delete={() => {
											selectedItem = item;
											showDeleteConfirm = true;
										}}
										on:openMenu={() => {
											menuIdOpened = item.id
										}}
										on:closeMenu={() => {
											menuIdOpened = null
										}}
									/>
								</div>
								{/if}
							</div>

							<div class="self-center flex-1 px-1 mb-1">
								<div class="text-left line-clamp-2 h-fit text-base {(hoveredKowledge === item.id || menuIdOpened === item.id) ? 'dark:text-white' : 'dark:text-customGray-100'} text-lightGray-100 leading-[1.2] mb-1.5">{item.name}</div>
								<div class="mb-5 text-left overflow-hidden text-ellipsis line-clamp-1 text-xs text-lightGray-1200 dark:text-customGray-100/50">
									{item.description}
								</div>
							</div>
						</div>
						<div class="flex justify-between mt-auto items-center px-0.5 pt-2.5 pb-[2px] border-t border-[#A7A7A7]/10 dark:border-customGray-700">
							<div class="text-xs text-lightGray-1200 dark:text-customGray-100 flex items-center">
								{#if item?.user?.profile_image_url}
									<img class="w-3 h-3 rounded-full mr-1" src={item?.user?.profile_image_url} alt={item?.user?.first_name ?? item?.user?.email ?? $i18n.t('Deleted User')}/>
								{/if}
								<Tooltip
									content={item?.user?.email ?? $i18n.t('Deleted User')}
									className="flex shrink-0"
									placement="top-start"
								>
								{#if (item?.user?.first_name && item?.user?.last_name)}
									{item?.user?.first_name} {item?.user?.last_name}
								{:else if (item?.user?.email)}
									{item?.user?.email}
								{:else}
									{$i18n.t('Deleted User')}
								{/if}
								</Tooltip>
							</div>
							<div class=" text-xs text-gray-500 line-clamp-1 dark:text-customGray-100/50">
								{dayjs(item.updated_at * 1000).format('DD.MM.YYYY')}
							</div>
						</div>
					</button>
				{/each}
			</div>
		</div>
	</div>

	<!-- 
	<div class="mb-5 grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-2">
		{#each filteredItems as item}
			<button
				class=" flex space-x-4 cursor-pointer text-left w-full px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-850 transition rounded-xl"
				on:click={() => {
					if (item?.meta?.document) {
						toast.error(
							$i18n.t(
								'Only collections can be edited, create a new knowledge base to edit/add documents.'
							)
						);
					} else {
						goto(`/workspace/knowledge/${item.id}`);
					}
				}}
			>
				<div class=" w-full">
					<div class="flex items-center justify-between -mt-1">
						{#if item?.meta?.document}
							<Badge type="muted" content={$i18n.t('Document')} />
						{:else}
							<Badge type="success" content={$i18n.t('Collection')} />
						{/if}

						<div class=" flex self-center -mr-1 translate-y-1">
							<ItemMenu
								on:delete={() => {
									selectedItem = item;
									showDeleteConfirm = true;
								}}
							/>
						</div>
					</div>

					<div class=" self-center flex-1 px-1 mb-1">
						<div class=" font-semibold line-clamp-1 h-fit">{item.name}</div>

						<div class=" text-xs overflow-hidden text-ellipsis line-clamp-1">
							{item.description}
						</div>

						<div class="mt-3 flex justify-between">
							<div class="text-xs text-gray-500">
								<Tooltip
									content={item?.user?.email ?? $i18n.t('Deleted User')}
									className="flex shrink-0"
									placement="top-start"
								>
									{$i18n.t('By {{name}}', {
										name: capitalizeFirstLetter(
											item?.user?.name ?? item?.user?.email ?? $i18n.t('Deleted User')
										)
									})}
								</Tooltip>
							</div>
							<div class=" text-xs text-gray-500 line-clamp-1">
								{$i18n.t('Updated')}
								{dayjs(item.updated_at * 1000).fromNow()}
							</div>
						</div>
					</div>
				</div>
			</button>
		{/each}
	</div>

	<div class=" text-gray-500 text-xs mt-1 mb-2">
		ⓘ {$i18n.t("Use '#' in the prompt input to load and include your knowledge.")}
	</div>-->
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}
