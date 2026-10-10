<script lang="ts">
	import WorkspaceAccessModal from './common/WorkspaceAccessModal.svelte';
	let accessModal: WorkspaceAccessModal;
	import { resolveLocalizedResource } from '$lib/utils/localizedContent';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	dayjs.extend(relativeTime);

	import { onMount, getContext, tick, onDestroy } from 'svelte';
	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	import {
		WEBUI_NAME,
		user,
		skills as _skills,
		workspaceActions,
		workspaceCounts
	} from '$lib/stores';
	import { goto } from '$app/navigation';
	import {
		getSkills,
		getSkillItems,
		exportSkills,
		deleteSkillById,
		toggleSkillById
	} from '$lib/apis/skills';
	import { capitalizeFirstLetter } from '$lib/utils';
	import TagInput from '$lib/components/common/Tags/TagInput.svelte';

	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Search from '../icons/Search.svelte';
	import XMark from '../icons/XMark.svelte';
	import Spinner from '../common/Spinner.svelte';
	import ViewSelector from './common/ViewSelector.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Switch from '../common/Switch.svelte';
	import SkillMenu from './Skills/SkillMenu.svelte';
	import CommunityDiscover from './common/CommunityDiscover.svelte';
	import { config } from '$lib/stores';
	let stopSkillShare = () => {};
	const shareHandler = (skill: { id: string }) => {
		stopSkillShare();
		const tab = window.open('https://openwebui.com/post?type=skill', '_blank');
		if (!tab) {
			toast.error($i18n.t('Please allow popups to share your skill.'));
			return;
		}
		const receiveLoaded = async (event: MessageEvent) => {
			if (
				event.origin !== 'https://openwebui.com' ||
				event.source !== tab ||
				event.data !== 'loaded'
			)
				return;
			stopSkillShare();
			try {
				const exported = JSON.parse(
					await (await exportSkillBundle(localStorage.token, 'json', [skill.id])).text()
				);
				const { id, name, description, files } = Array.isArray(exported) ? exported[0] : exported;
				const data = JSON.stringify({ id, name, description, files });
				if (new Blob([data]).size > 15 * 1024 * 1024)
					throw new Error('Community skill JSON exceeds 15 MiB');
				tab.postMessage(data, 'https://openwebui.com');
			} catch (error) {
				toast.error(skillError(error));
			}
		};
		window.addEventListener('message', receiveLoaded);
		stopSkillShare = () => window.removeEventListener('message', receiveLoaded);
	};
	import SkillImport from './Skills/SkillImport.svelte';
	import ImportModal from '$lib/components/ImportModal.svelte';
	import { cloneSkill, exportSkillBundle, loadSkillByUrl, skillError } from '$lib/apis/skills';
	let showImport = false;
	let showImportFromLink = false;
	let bundleFiles: File[] = [];
	let folderImportInput: HTMLInputElement;
	import Pagination from '../common/Pagination.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';

	let shiftKey = false;
	let loaded = false;

	let importInputElement: HTMLInputElement;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let searchController: AbortController;

	let selectedSkill = null;
	let showDeleteConfirm = false;

	let filteredItems = null;
	let total = null;
	let loading = false;

	let tagsContainerElement: HTMLDivElement;
	let viewOption = '';
	let sortKey = 'updated_at';
	let sortDirection = 'desc';
	let openSkillMenuId: string | null = null;
	let page = 1;

	$: if (loaded) {
		workspaceActions.set([
			{
				id: 'skills-new',
				label: $i18n.t('Create'),
				href: '/workspace/skills/create',
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.skills
			},
			{
				id: 'skills-import',
				label: $i18n.t('Import'),
				onClick: () => importInputElement?.click(),
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.skills_import
			},
			{
				id: 'skills-import-url',
				label: $i18n.t('Import from URL'),
				onClick: () => {
					showImportFromLink = true;
				},
				visible: $user?.role === 'admin'
			},
			{
				id: 'skills-import-folder',
				label: 'Import folder',
				onClick: () => folderImportInput?.click(),
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.skills_import
			},
			{
				id: 'skills-export-zip',
				label: 'Export ZIP',
				onClick: async () => {
					try {
						saveAs(await exportSkillBundle(localStorage.token, 'zip'), 'skills.zip');
					} catch (error) {
						toast.error(skillError(error));
					}
				},
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.skills_export
			},
			{
				id: 'skills-export',
				label: $i18n.t('Export JSON'),
				onClick: async () => {
					const _skills = await exportSkills(localStorage.token).catch((error) => {
						toast.error(`${error}`);
						return null;
					});
					if (_skills) {
						let blob = new Blob([JSON.stringify(_skills)], {
							type: 'application/json'
						});
						saveAs(blob, `skills-export-${Date.now()}.json`);
					}
				},
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.skills_export
			}
		]);
	}

	const loadSkillItems = async () => {
		if (!loaded) return;

		clearTimeout(searchDebounceTimer);
		searchController?.abort();
		searchController = new AbortController();
		const { signal } = searchController;

		loading = true;
		try {
			const res = await getSkillItems(
				localStorage.token,
				query,
				viewOption,
				page,
				sortKey,
				sortDirection,
				signal
			).catch((error) => {
				if (!signal.aborted) toast.error(`${error}`);
				return null;
			});

			if (signal.aborted) return;

			if (res) {
				filteredItems = res.items;
				total = res.total;
				workspaceCounts.update((counts) => ({ ...counts, skills: total }));
			}
		} catch (err) {
			console.error(err);
		} finally {
			if (!signal.aborted) loading = false;
		}
	};

	const handleSearchInput = () => {
		searchController?.abort();
		loading = true;
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (page !== 1) {
				page = 1;
			} else {
				loadSkillItems();
			}
		}, 300);
	};

	// Immediate response to page/filter changes
	$: if (
		loaded &&
		page &&
		viewOption !== undefined &&
		sortKey !== undefined &&
		sortDirection !== undefined
	) {
		loadSkillItems();
	}

	const setSortKey = (key: string) => {
		if (sortKey === key) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDirection = key === 'updated_at' ? 'desc' : 'asc';
		}
	};

	const openSkill = (skill) => {
		goto(`/workspace/skills/edit?id=${encodeURIComponent(skill.id)}`);
	};

	const shouldIgnoreRowClick = (target: EventTarget | null) => {
		return target instanceof Element && !!target.closest('button, a, input, [role="menu"]');
	};

	const cloneHandler = async (skill) => {
		try {
			const suffix = crypto.randomUUID().slice(0, 7);
			const result = await cloneSkill(
				localStorage.token,
				skill.id,
				`${skill.name} (${suffix})`,
				`${skill.id}-${suffix}`
			);
			await goto(`/workspace/skills/edit?id=${result.id}`);
		} catch (error) {
			toast.error(skillError(error));
		}
	};

	const exportHandler = async (skill, format: 'json' | 'zip' = 'json') => {
		try {
			saveAs(
				await exportSkillBundle(localStorage.token, format, [skill.id]),
				`${skill.id}.${format}`
			);
		} catch (error) {
			toast.error(skillError(error));
		}
	};

	const deleteHandler = async (skill) => {
		const res = await deleteSkillById(localStorage.token, skill.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Skill deleted successfully'));
		}

		page = 1;
		loadSkillItems();
		await _skills.set(await getSkills(localStorage.token));
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
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
			clearTimeout(searchDebounceTimer);
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);
		};
	});

	onDestroy(() => {
		stopSkillShare();
		searchController?.abort();
		clearTimeout(searchDebounceTimer);
	});
</script>

<WorkspaceAccessModal bind:this={accessModal} resourceType="skills" onUpdated={loadSkillItems} />

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title>
		{$i18n.t('Skills')} / {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<ImportModal
		bind:show={showImportFromLink}
		loadUrlHandler={(url) => loadSkillByUrl(localStorage.token, url)}
		transformResult={(packages) => packages}
		successMessage={$i18n.t('Skills loaded for preview')}
		onImport={(packages) => {
			bundleFiles = [
				new File([JSON.stringify(packages)], 'skills.json', { type: 'application/json' })
			];
			showImport = true;
		}}
	/>
	{#key bundleFiles}
		<SkillImport
			bind:show={showImport}
			files={bundleFiles}
			onImported={async () => {
				toast.success($i18n.t('Skill imported successfully'));
				page = 1;
				await loadSkillItems();
				_skills.set(await getSkills(localStorage.token));
			}}
		/>
	{/key}
	<input
		bind:this={importInputElement}
		type="file"
		accept=".md,.json,.zip"
		multiple
		hidden
		on:change={() => {
			bundleFiles = Array.from(importInputElement.files || []);
			showImport = true;
			importInputElement.value = '';
		}}
	/>
	<input
		bind:this={folderImportInput}
		type="file"
		webkitdirectory
		multiple
		hidden
		on:change={() => {
			bundleFiles = Array.from(folderImportInput.files || []);
			showImport = true;
			folderImportInput.value = '';
		}}
	/>

	<div class="space-y-1">
		<div class="flex h-8 w-full items-center gap-2">
			<div class="flex min-w-0 flex-1">
				<div class=" self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					on:input={handleSearchInput}
					aria-label={$i18n.t('Search Skills')}
					placeholder={$i18n.t('Search Skills')}
				/>
				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							aria-label={$i18n.t('Clear search')}
							on:click={() => {
								query = '';
								handleSearchInput();
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>

			<div
				class="flex max-w-[55%] shrink-0 overflow-x-auto scrollbar-none"
				bind:this={tagsContainerElement}
				on:wheel={(e) => {
					if (e.deltaY !== 0) {
						e.preventDefault();
						e.currentTarget.scrollLeft += e.deltaY;
					}
				}}
			>
				<div
					class="flex w-fit gap-0.5 text-center text-sm rounded-full bg-transparent whitespace-nowrap"
				>
					<ViewSelector
						bind:value={viewOption}
						align="end"
						onChange={async (value) => {
							localStorage.workspaceViewOption = value;
							page = 1;
							await tick();
						}}
					/>
				</div>
			</div>
		</div>

		{#if filteredItems === null || loading}
			<div class="w-full h-full flex justify-center items-center my-16 mb-24">
				<Spinner className="size-5" />
			</div>
		{:else if (filteredItems ?? []).length !== 0}
			<div class="my-1">
				<div
					class="flex w-full items-center gap-2 px-1.5 pb-0.5 text-xs text-gray-400 dark:text-gray-600"
				>
					<button
						class="flex min-w-0 flex-1 items-center gap-1 py-0.5 text-left"
						type="button"
						on:click={() => setSortKey('name')}
					>
						{$i18n.t('Title')}
						{#if sortKey === 'name'}
							{#if sortDirection === 'asc'}
								<ChevronUp className="size-2" />
							{:else}
								<ChevronDown className="size-2" />
							{/if}
						{/if}
					</button>

					<div class="hidden w-44 shrink-0 md:block"></div>

					<button
						class="flex w-36 shrink-0 items-center justify-end gap-1 py-0.5 text-right"
						type="button"
						on:click={() => setSortKey('updated_at')}
					>
						{$i18n.t('Updated at')}
						{#if sortKey === 'updated_at'}
							{#if sortDirection === 'asc'}
								<ChevronUp className="size-2" />
							{:else}
								<ChevronDown className="size-2" />
							{/if}
						{/if}
					</button>
				</div>

				<div class="grid gap-y-0.5">
					{#each filteredItems as skill (skill.id)}
						<div
							class="group flex min-h-8 w-full cursor-pointer items-center gap-2 overflow-hidden rounded-xl px-2 py-1 text-left"
							role="button"
							tabindex="0"
							on:click={(e) => {
								if (shouldIgnoreRowClick(e.target)) return;
								openSkill(skill);
							}}
							on:keydown={(e) => {
								if (e.currentTarget !== e.target) return;
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									openSkill(skill);
								}
							}}
						>
							<div class="flex min-w-0 flex-1 items-center gap-1 overflow-hidden">
								<div class="flex min-w-0 flex-1 flex-col overflow-hidden">
									<div class="flex min-w-0 items-center gap-2 overflow-hidden">
										<div class="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
											<Tooltip content={skill.id} className="min-w-0" placement="top-start">
												<div
													class="truncate text-[0.8125rem] leading-5 text-gray-800 group-hover:underline dark:text-gray-200"
												>
													{resolveLocalizedResource(skill, $i18n.language)}
												</div>
											</Tooltip>

											<div
												class="min-w-0 max-w-[40%] shrink-0 truncate text-[0.6875rem] leading-5 text-gray-500"
											>
												/{skill.id}
											</div>

											<Tooltip
												content={dayjs((skill.updated_at ?? skill.created_at) * 1000)
													.locale($i18n.language)
													.format('LLLL')}
											>
												<div
													class="shrink-0 truncate text-[0.6875rem] leading-5 text-gray-400 dark:text-gray-600"
												>
													{dayjs((skill.updated_at ?? skill.created_at) * 1000)
														.locale($i18n.language)
														.fromNow()}
												</div>
											</Tooltip>

											{#if !skill.is_active}
												<Badge type="muted" content={$i18n.t('Inactive')} />
											{/if}

											{#if !skill.write_access}
												<Badge type="muted" content={$i18n.t('Read Only')} />
											{/if}
										</div>
									</div>

									{#if resolveLocalizedResource(skill, $i18n.language, 'description')}
										<Tooltip
											content={resolveLocalizedResource(skill, $i18n.language, 'description')}
											className="min-w-0"
											placement="top-start"
										>
											<div
												class="mt-0.5 truncate text-[0.6875rem] leading-4 text-gray-400 dark:text-gray-600"
											>
												{resolveLocalizedResource(skill, $i18n.language, 'description')}
											</div>
										</Tooltip>
									{/if}
								</div>
							</div>

							<div
								class="hidden max-w-44 shrink-0 self-center truncate text-right text-[0.6875rem] leading-5 text-gray-500 dark:text-gray-500 md:block"
							>
								<Tooltip
									content={skill?.user?.email ?? $i18n.t('Deleted User')}
									className="min-w-0"
									placement="top-start"
								>
									<div class="truncate">
										{capitalizeFirstLetter(
											skill?.user?.name ?? skill?.user?.email ?? $i18n.t('Deleted User')
										)}
									</div>
								</Tooltip>
							</div>

							{#if skill.write_access}
								<div class="ml-2 flex shrink-0 flex-row items-center self-center">
									{#if shiftKey}
										<Tooltip content={$i18n.t('Delete')}>
											<button
												class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition dark:text-gray-500"
												type="button"
												aria-label={$i18n.t('Delete')}
												on:click={(e) => {
													e.preventDefault();
													e.stopPropagation();
													deleteHandler(skill);
												}}
											>
												<GarbageBin className="size-4" />
											</button>
										</Tooltip>
									{:else}
										<div class="flex shrink-0 flex-row items-center gap-1.5 self-center">
											<SkillMenu
												shareHandler={() => shareHandler(skill)}
												accessHandler={() => accessModal.open(skill.id)}
												show={openSkillMenuId === skill.id}
												editHandler={() => {
													goto(`/workspace/skills/edit?id=${encodeURIComponent(skill.id)}`);
												}}
												cloneHandler={() => {
													cloneHandler(skill);
												}}
												exportHandler={(format) => {
													exportHandler(skill, format);
												}}
												deleteHandler={async () => {
													selectedSkill = skill;
													showDeleteConfirm = true;
												}}
												onClose={() => {
													openSkillMenuId = null;
												}}
											>
												<button
													class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition dark:text-gray-500"
													type="button"
													aria-label={$i18n.t('Skill Menu')}
													on:click={(e) => {
														e.preventDefault();
														e.stopPropagation();
														openSkillMenuId = openSkillMenuId === skill.id ? null : skill.id;
													}}
												>
													<EllipsisHorizontal className="size-4" />
												</button>
											</SkillMenu>

											<button
												class="flex h-6 items-center"
												type="button"
												on:click={(e) => {
													e.stopPropagation();
													e.preventDefault();
												}}
											>
												<Tooltip
													content={skill.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}
												>
													<Switch
														bind:state={skill.is_active}
														on:change={async () => {
															await toggleSkillById(localStorage.token, skill.id);
															_skills.set(await getSkills(localStorage.token));
														}}
													/>
												</Tooltip>
											</button>
										</div>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			</div>

			{#if total > 30}
				<div class="flex justify-center mt-4 mb-2">
					<Pagination bind:page count={total} perPage={30} />
				</div>
			{/if}
		{:else}
			<div class="flex w-full flex-col items-center justify-center py-16 pb-24">
				<div class="max-w-sm text-center text-gray-900 dark:text-gray-100">
					<div class="mb-1.5 text-sm">{$i18n.t('No skills found')}</div>
					<div class="text-center text-xs leading-5 text-gray-500">
						{$i18n.t('Try adjusting your search or filter to find what you are looking for.')}
					</div>
				</div>
			</div>
		{/if}
	</div>

	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete skill?')}
		on:confirm={() => {
			deleteHandler(selectedSkill);
		}}
	>
		<div class=" text-sm text-gray-500 truncate">
			{$i18n.t('This will delete')}
			<span class="  font-normal">{resolveLocalizedResource(selectedSkill, $i18n.language)}</span>.
		</div>
	</DeleteConfirmDialog>
	{#if $config?.features?.enable_community_sharing}
		<CommunityDiscover
			href="https://openwebui.com/search?type=skill"
			title={$i18n.t('Discover a skill')}
			description={$i18n.t('Discover, download, and explore community skills')}
		/>
	{/if}
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
