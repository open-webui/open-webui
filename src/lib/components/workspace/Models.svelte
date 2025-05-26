<script lang="ts">
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';
	import Sortable from 'sortablejs';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	const i18n = getContext('i18n');

	import {
		WEBUI_NAME,
		config,
		mobile,
		models as _models,
		settings,
		user,
		showSidebar
	} from '$lib/stores';
	import {
	bookmarkModel,
		createNewModel,
		deleteModelById,
		getModels as getWorkspaceModels,
		toggleModelById,
		updateModelById
	} from '$lib/apis/models';

	import { getModels } from '$lib/apis';
	import { getGroups } from '$lib/apis/groups';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import ModelMenu from './Models/ModelMenu.svelte';
	import ModelDeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Switch from '../common/Switch.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { capitalizeFirstLetter } from '$lib/utils';
	import ShowSidebarIcon from '../icons/ShowSidebarIcon.svelte';
	import GroupIcon from '../icons/GroupIcon.svelte';
	import PublicIcon from '../icons/PublicIcon.svelte';
	import PrivateIcon from '../icons/PrivateIcon.svelte';
	import dayjs from 'dayjs';
	import MenuIcon from '../icons/MenuIcon.svelte';
	import FilterDropdown from './Models/FilterDropdown.svelte';
	import BackIcon from '../icons/BackIcon.svelte';
	import BookIcon from '../icons/BookIcon.svelte';
	import BookmarkIcon from '../icons/BookmarkIcon.svelte';
	import BookmarkedIcon from '../icons/BookmarkedIcon.svelte';



	let shiftKey = false;

	let importFiles;
	let modelsImportInputElement: HTMLInputElement;
	let loaded = false;

	let models = [];

	let filteredModels = [];
	let selectedModel = null;

	let showModelDeleteConfirm = false;

	let group_ids = [];

	let tags = [];
	let selectedTags = new Set();
	let accessFilter = 'all';
	let groupsForModels;

	$: if (models) {
		tags = Array.from(
			new Set(models.flatMap((m) => m.meta?.tags?.map((t) => t.name.toLowerCase()) || []))
		);
	}

	$: if (models) {
		filteredModels = models.filter((m) => {
			const nameMatch =
				searchValue === '' || m.name.toLowerCase().includes(searchValue.toLowerCase());

			const modelTags = m.meta?.tags?.map((t) => t.name.toLowerCase()) || [];

			const tagsMatch =
				selectedTags.size === 0 || Array.from(selectedTags).some((tag) => modelTags.includes(tag));

			const isPublic = m.access_control === null;
			// const isPrivate = m.access_control !== null;
			const isPrivate = m?.user_id === $user?.id;
			const accessMatch =
				accessFilter === 'all' ||
				(accessFilter === 'public' && isPublic) ||
				(accessFilter === 'private' && isPrivate);

			return nameMatch && tagsMatch && accessMatch;
		});
	}

	let searchValue = '';
	let showInput = false;

	const deleteModelHandler = async (model) => {
		const res = await deleteModelById(localStorage.token, model.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: model.id }));
		}

		await _models.set(await getModels(localStorage.token));
		models = await getWorkspaceModels(localStorage.token);
	};

	const cloneModelHandler = async (model) => {
		sessionStorage.model = JSON.stringify({
			...model,
			id: `${model.id}-clone`,
			name: `${model.name} (Clone)`
		});
		goto('/workspace/models/create');
	};

	const shareModelHandler = async (model) => {
		toast.success($i18n.t('Redirecting you to OpenWebUI Community'));

		const url = 'https://openwebui.com';

		const tab = await window.open(`${url}/models/create`, '_blank');

		// Define the event handler function
		const messageHandler = (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(model), '*');

				// Remove the event listener after handling the message
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
	};

	const hideModelHandler = async (model) => {
		let info = model.info;

		if (!info) {
			info = {
				id: model.id,
				name: model.name,
				meta: {
					suggestion_prompts: null
				},
				params: {}
			};
		}

		info.meta = {
			...info.meta,
			hidden: !(info?.meta?.hidden ?? false)
		};

		const res = await updateModelById(localStorage.token, info.id, info);

		if (res) {
			toast.success(
				$i18n.t(`Model {{name}} is now {{status}}`, {
					name: info.id,
					status: info.meta.hidden ? 'hidden' : 'visible'
				})
			);
		}

		await _models.set(await getModels(localStorage.token));
		models = await getWorkspaceModels(localStorage.token);
	};

	const downloadModels = async (models) => {
		let blob = new Blob([JSON.stringify(models)], {
			type: 'application/json'
		});
		saveAs(blob, `models-export-${Date.now()}.json`);
	};

	const exportModelHandler = async (model) => {
		let blob = new Blob([JSON.stringify([model])], {
			type: 'application/json'
		});
		saveAs(blob, `${model.id}-${Date.now()}.json`);
	};

	onMount(async () => {
		models = await getWorkspaceModels(localStorage.token);
		let groups = await getGroups(localStorage.token);
		groupsForModels = groups;
		group_ids = groups.map((group) => group.id);

		loaded = true;

		const onKeyDown = (event) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event) => {
			if (event.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onBlur = () => {
			shiftKey = false;
		};

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur', onBlur);

		return () => {
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);
		};
	});

	const formatter = new Intl.DateTimeFormat('de-DE', {
		day: '2-digit',
		month: '2-digit',
		year: 'numeric'
	});

	function getGroupNamesFromAccess(model) {
		if (!model.access_control) return [];

		const readGroups = model.access_control.read?.group_ids || [];
		const writeGroups = model.access_control.write?.group_ids || [];

		const allGroupIds = Array.from(new Set([...readGroups, ...writeGroups]));

		const matchedGroups = allGroupIds
			.map((id) => groupsForModels.find((g) => g.id === id))
			.filter(Boolean)
			.map((g) => g.name);

		return matchedGroups;
	}

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
	
	let logoSrc = '/logo_light.png';
	// onMount(() => {
	// 	const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
	// 	logoSrc = isDark ? '/logo_light.png' : '/logo_dark.png';
	// });

	$: if (loaded) {
		setTimeout(() => {
			updateScrollHeight();
		}, 0);
	}
	let hoveredModel = null;
	let menuIdOpened = null;

	$: console.log(filteredModels, 'filtered Models')

	const bookmarkAssistant = async (id, bookmarkedModel) => {
		const bookmarked = !bookmarkedModel;
		const res = await bookmarkModel(localStorage.token, id, bookmarked);
		if (res) {
			_models.set(await getModels(localStorage.token));
			models = await getWorkspaceModels(localStorage.token);
		}
	}
	
</script>

<svelte:head>
	<title>
		{$i18n.t('Models')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<ModelDeleteConfirmDialog
		bind:show={showModelDeleteConfirm}
		on:confirm={() => {
			deleteModelHandler(selectedModel);
		}}
	/>

	<div
		id="assistants-header"
		class="pl-4 md:pl-[22px] pr-4 py-2.5 border-b border-lightGray-400 dark:border-customGray-700"
	>
		<div class="flex justify-between items-center">
			<div class="flex items-center">
				<div class="{$showSidebar ? 'md:hidden' : ''} self-center flex flex-none items-center">
					{#if ($mobile)}
						<button class="flex items-center gap-1" on:click={() => history.back()}>
							<BackIcon />
							<div class="flex items-center md:self-center text-base font-medium leading-none px-0.5 text-lightGray-100 dark:text-customGray-100">
								{$i18n.t('Assistants')}
							</div>
						</button>
					{:else}
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
					{/if}
				</div>
				{#if (!$mobile)}
					<div class="flex items-center md:self-center text-base font-medium leading-none px-0.5 text-lightGray-100 dark:text-customGray-100">
						{$i18n.t('Assistants')}
					</div>
				{/if}
			</div>
			<div class="flex">
				<div
					class="flex flex-1 items-center p-2.5 rounded-lg mr-1 border border-lightGray-400 dark:border-customGray-700 hover:bg-lightGray-700 dark:hover:bg-customGray-950 dark:hover:text-white transition"
				>
					<!-- <div class=" self-center ml-1 mr-3"> -->
					<button
						class=""
						on:click={() => {
							showInput = !showInput;
							if (!showInput) searchValue = '';
						}}
						aria-label="Toggle Search"
					>
						<Search className="size-3.5" />
					</button>
					<!-- </div> -->
					{#if showInput}
						<input
							class=" w-[5rem] md:w-full text-xs outline-none bg-transparent leading-none pl-2"
							bind:value={searchValue}
							placeholder={$i18n.t('Search Models')}
							autofocus
							on:blur={() => {
								if (searchValue.trim() === '') showInput = false;
							}}
						/>
					{/if}
				</div>
				<div>
					<a
						class=" px-2 py-2.5 md:w-[220px] rounded-lg leading-none border border-lightGray-400 dark:border-customGray-700 hover:bg-lightGray-700 dark:hover:bg-customGray-950 text-lightGray-100 dark:text-customGray-200 dark:hover:text-white transition font-medium text-xs flex items-center justify-center space-x-1"
						href="/workspace/models/create"
					>
						<Plus className="size-3.5" />
						<span class="">{$i18n.t('Create new')}</span>
					</a>
				</div>
			</div>
		</div>
	</div>
	<div class="pl-4 md:pl-[22px] pr-4">
		<div
			id="assistants-filters"
			class="flex items-start justify-between pt-5 pb-3 md:pt-5 md:pb-5 md:pr-[22px] flex-row"
		>
			<div class="flex items-center md:items-start space-x-[5px] flex-col sm:flex-row mb-3 sm:mb-0">
				{#if ($mobile)}
				<FilterDropdown>
					<div class="flex flex-wrap gap-1">
						{#each tags as tag}
							<button
								class={`flex items-center justify-center rounded-md text-xs leading-none px-[6px] py-[6px] ${selectedTags.has(tag) ? 'bg-customViolet-200 dark:bg-customBlue-800' : 'bg-lightGray-400  dark:bg-customGray-800 '} font-medium text-lightGray-100 dark:text-white`}
								on:click={() => {
									selectedTags.has(tag) ? selectedTags.delete(tag) : selectedTags.add(tag);
									selectedTags = new Set(selectedTags);
								}}
							>
								{tag.charAt(0).toUpperCase() + tag.slice(1)}
							</button>
						{/each}
					</div>
				</FilterDropdown>
				{:else}
				<div
					class="font-medium text-lightGray-100 dark:text-customGray-300 text-xs whitespace-nowrap h-[22px] flex items-center md:mb-2 sm:mb-0"
				>
					{$i18n.t('Filter by category')}
				</div>
				<div class="flex flex-wrap gap-1">
					{#each tags as tag}
						<button
							class={`flex items-center justify-center rounded-md text-xs leading-none px-[6px] py-[6px] ${selectedTags.has(tag) ? 'bg-customViolet-200 dark:bg-customBlue-800' : 'bg-lightGray-400 hover:bg-customViolet-200 dark:bg-customGray-800 dark:hover:bg-customGray-950'} font-medium text-lightGray-100 dark:text-white`}
							on:click={() => {
								selectedTags.has(tag) ? selectedTags.delete(tag) : selectedTags.add(tag);
								selectedTags = new Set(selectedTags);
							}}
						>
							{tag.charAt(0).toUpperCase() + tag.slice(1)}
						</button>
					{/each}
				</div>
				{/if}
			</div>
			<div class="flex bg-lightGray-700 dark:bg-customGray-800 rounded-md flex-shrink-0">
				<button
					on:click={() => (accessFilter = 'all')}
					class={`${accessFilter === 'all' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-4 md:px-[23px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('All')}</button
				>
				<button
					on:click={() => (accessFilter = 'private')}
					class={`${accessFilter === 'private' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-4 md:px-[23px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('My Assistants')}</button
				>
				<button
					on:click={() => (accessFilter = 'public')}
					class={`${accessFilter === 'public' ? 'bg-lightGray-400 text-lightGray-100 dark:bg-customGray-900 rounded-md border border-lightGray-250 dark:border-customGray-700' : 'text-lightGray-100/70'} font-medium px-4 md:px-[23px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white`}
					>{$i18n.t('Public')}</button
				>
				<!-- <button class="px-[23px] py-[7px] flex-shrink-0 text-xs leading-none dark:text-white"
					>{$i18n.t('Pre-built')}</button
				> -->
			</div>
		</div>
		<div
			id="models-scroll-container"
			bind:this={scrollContainer}
			class="overflow-y-scroll pr-[3px]"
		>
			{#if models?.length < 1}
				<div class="flex h-[calc(100dvh-200px)] w-full justify-center items-center">
					<div class="text-sm dark:text-customGray-100/50">{$i18n.t('No assistants added yet')}</div>
				</div>
			{/if}
			<div class="mb-2 gap-2 grid lg:grid-cols-2 xl:grid-cols-3" id="model-list">
				{#each filteredModels as model (model.id)}
					<div
						on:mouseenter={() => hoveredModel = model.id}
						on:mouseleave={() => hoveredModel = null}
						class="flex flex-col gap-y-1 cursor-pointer w-full px-3 py-2 bg-lightGray-550 dark:bg-customGray-800 rounded-2xl transition"
						id="model-item-{model.id}"
					>
						<div class="flex items-start justify-between">
							<div class="flex items-center">
								<button on:click={() => bookmarkAssistant(model.id, model.bookmarked)} class="text-lightGray-100 dark:text-customGray-300">
									{#if model?.bookmarked}
										<BookmarkedIcon/>
									{:else}
										<BookmarkIcon/>
									{/if}
									
								</button>
								<div class="flex items-center gap-1 flex-wrap">
									{#if model.access_control == null}
										<div
											class="flex gap-1 items-center {(hoveredModel === model.id || menuIdOpened === model.id) ? 'dark:text-white' : 'text-lightGray-100 dark:text-customGray-300'} text-xs bg-lightGray-400 font-medium dark:bg-customGray-900 px-[6px] py-[3px] rounded-md"
										>
											<PublicIcon />
											<span>{$i18n.t('Public')}</span>
										</div>
									{:else if getGroupNamesFromAccess(model).length < 1}
										<div
											class="flex gap-1 items-center {(hoveredModel === model.id || menuIdOpened === model.id) ? 'dark:text-white' : 'text-lightGray-100 dark:text-customGray-300'} text-xs bg-lightGray-400 font-medium dark:bg-customGray-900 px-[6px] py-[3px] rounded-md"
										>
											<PrivateIcon />
											<span>{$i18n.t('Private')}</span>
										</div>
									{:else}
										{#each getGroupNamesFromAccess(model) as groupName}
											<div
												class="flex items-center {(hoveredModel === model.id || menuIdOpened === model.id) ? 'dark:text-white' : 'text-lightGray-100 dark:text-customGray-300'} text-xs bg-lightGray-400 font-medium dark:bg-customGray-900 px-[6px] py-[3px] rounded-md"
											>
												<GroupIcon />
												<span>{groupName}</span>
											</div>
										{/each}
									{/if}

									{#each model.meta?.tags as modelTag}
										<div
											class="flex items-center {(hoveredModel === model.id || menuIdOpened === model.id) ? 'dark:text-white' : 'text-lightGray-100 dark:text-customGray-100'} text-xs bg-customViolet-200 dark:bg-customBlue-800 px-[6px] py-[3px] rounded-md"
										>
											{modelTag.name}
										</div>
									{/each}
								</div>
							</div>
							{#if $user?.role === 'admin' || model.user_id === $user?.id || model?.access_control?.write.group_ids?.some( (wg) => group_ids.includes(wg) )}
							<div class="{(hoveredModel === model.id || menuIdOpened === model.id) ? 'md:visible' : 'md:invisible'} ">
								<ModelMenu
									user={$user}
									{model}
									shareHandler={() => {
										shareModelHandler(model);
									}}
									cloneHandler={() => {
										cloneModelHandler(model);
									}}
									exportHandler={() => {
										exportModelHandler(model);
									}}
									hideHandler={() => {
										hideModelHandler(model);
									}}
									deleteHandler={() => {
										selectedModel = model;
										showModelDeleteConfirm = true;
									}}
									onClose={() => {}}
									on:openMenu={() => {
										menuIdOpened = model.id
									}}
									on:closeMenu={() => {
										menuIdOpened = null
									}}
								>
									<button
										class="self-center w-fit text-sm px-0.5 h-[21px] dark:text-white dark:hover:text-white hover:bg-black/5  rounded-md"
										type="button"
									>
										<EllipsisHorizontal className="size-5" />
									</button>
								</ModelMenu>
							</div>
							{/if}
						</div>
						<div class="flex gap-4 mb-2.5">
							<div class=" w-[56px]">
								<div
									class=" rounded-full object-cover {model.is_active
										? ''
										: 'opacity-50 dark:opacity-50'} "
								>
									<img
										src={!model?.meta?.profile_image_url ||
										model?.meta?.profile_image_url === '/static/favicon.png'
											? logoSrc
											: model?.meta?.profile_image_url}
										alt="modelfile profile"
										class=" rounded-md w-full h-auto object-cover"
									/>
								</div>
							</div>

							<a
								class=" flex flex-1 cursor-pointer w-full"
								href={`/?models=${encodeURIComponent(model.id)}`}
							>
								<div class=" flex-1 self-center">
									
									<div class="text-base {(hoveredModel === model.id || menuIdOpened === model.id) ? 'dark:text-white' : 'text-lightGray-100 dark:text-customGray-100'}  line-clamp-2 leading-[1.2]">
										{model.name}
									</div>
								
									<div class="mt-[5px] flex gap-1 text-xs overflow-hidden">
										<div class="line-clamp-1 text-xs text-lightGray-1200 dark:text-customGray-100/50">
											{#if (model?.meta?.description ?? '').trim()}
												{model?.meta?.description}
											{/if}
										</div>
									</div>
								</div>
							</a>
						</div>

						<div
							class="flex justify-between mt-auto items-center px-0.5 pt-2.5 pb-[2px] border-t border-[#A7A7A7]/10 dark:border-customGray-700"
						>
							<div class=" text-xs mt-0.5">
								<Tooltip
									content={model?.user?.email ?? $i18n.t('Deleted User')}
									className="flex shrink-0 items-center"
									placement="top-start"
								>
									{#if model?.user?.profile_image_url}
										<img
											class="w-3 h-3 rounded-full mr-1"
											src={model?.user?.profile_image_url}
											alt={model?.user?.first_name ?? model?.user?.email ?? $i18n.t('Deleted User')}
										/>
									{/if}
									<div class="shrink-0 text-lightGray-1200 dark:text-customGray-100">
										{#if (model?.user?.first_name && model?.user?.last_name)}
											{model?.user?.first_name} {model?.user?.last_name}
										{:else if (model?.user?.email)}
											{model?.user?.email}
										{:else}
											{$i18n.t('Deleted User')}
										{/if}
									</div>
								</Tooltip>
							</div>
							<div class="text-xs text-lightGray-1200 dark:text-customGray-100/50">
								{dayjs(model.updated_at * 1000).format('DD.MM.YYYY')}
							</div>

							<!-- <div class="flex flex-row gap-0.5 items-center">
								{#if shiftKey}
									<Tooltip content={$i18n.t('Delete')}>
										<button
											class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											type="button"
											on:click={() => {
												deleteModelHandler(model);
											}}
										>
											<GarbageBin />
										</button>
									</Tooltip>
								{:else}
									{#if $user?.role === 'admin' || model.user_id === $user?.id || model.access_control.write.group_ids.some( (wg) => group_ids.includes(wg) )}
										<a
											class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											type="button"
											href={`/workspace/models/edit?id=${encodeURIComponent(model.id)}`}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="w-4 h-4"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
												/>
											</svg>
										</a>
									{/if}

									<div class="ml-1">
										<Tooltip content={model.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
											<Switch
												bind:state={model.is_active}
												on:change={async (e) => {
													toggleModelById(localStorage.token, model.id);
													_models.set(await getModels(localStorage.token));
												}}
											/>
										</Tooltip>
									</div>
								{/if}
							</div> -->
						</div>
					</div>
				{/each}
			</div>
		</div>
	</div>

	<!-- {#if $user?.role === 'admin'}
		<div class=" flex justify-end w-full mb-3">
			<div class="flex space-x-1">
				<input
					id="models-import-input"
					bind:this={modelsImportInputElement}
					bind:files={importFiles}
					type="file"
					accept=".json"
					hidden
					on:change={() => {
						console.log(importFiles);

						let reader = new FileReader();
						reader.onload = async (event) => {
							let savedModels = JSON.parse(event.target.result);
							console.log(savedModels);

							for (const model of savedModels) {
								if (model?.info ?? false) {
									if ($_models.find((m) => m.id === model.id)) {
										await updateModelById(localStorage.token, model.id, model.info).catch(
											(error) => {
												return null;
											}
										);
									} else {
										await createNewModel(localStorage.token, model.info).catch((error) => {
											return null;
										});
									}
								}
							}

							await _models.set(await getModels(localStorage.token));
							models = await getWorkspaceModels(localStorage.token);
						};

						reader.readAsText(importFiles[0]);
					}}
				/>

				<button
					class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
					on:click={() => {
						modelsImportInputElement.click();
					}}
				>
					<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Import Models')}</div>

					<div class=" self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-3.5 h-3.5"
						>
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</button>

				<button
					class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
					on:click={async () => {
						downloadModels($_models);
					}}
				>
					<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Export Models')}</div>

					<div class=" self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-3.5 h-3.5"
						>
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</button>
			</div>
		</div>
	{/if} -->

	<!-- {#if $config?.features.enable_community_sharing}
		<div class=" my-16">
			<div class=" text-xl font-medium mb-1 line-clamp-1">
				{$i18n.t('Made by OpenWebUI Community')}
			</div>

			<a
				class=" flex cursor-pointer items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-850 w-full mb-2 px-3.5 py-1.5 rounded-xl transition"
				href="https://openwebui.com/#open-webui-community"
				target="_blank"
			>
				<div class=" self-center">
					<div class=" font-semibold line-clamp-1">{$i18n.t('Discover a model')}</div>
					<div class=" text-sm line-clamp-1">
						{$i18n.t('Discover, download, and explore model presets')}
					</div>
				</div>

				<div>
					<div>
						<ChevronRight />
					</div>
				</div>
			</a>
		</div>
	{/if} -->
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}
