<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, user, skills as _skills, workspaceActions } from '$lib/stores';
	import { goto } from '$app/navigation';
	import {
		getSkills,
		getSkillById,
		getSkillItems,
		exportSkills,
		createNewSkill,
		deleteSkillById,
		toggleSkillById
	} from '$lib/apis/skills';
	import { capitalizeFirstLetter, parseFrontmatter, formatSkillName } from '$lib/utils';
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
	import Pagination from '../common/Pagination.svelte';

	let shiftKey = false;
	let loaded = false;

	let importFiles;
	let importInputElement: HTMLInputElement;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let selectedSkill = null;
	let showDeleteConfirm = false;

	let filteredItems = null;
	let total = null;
	let loading = false;

	let tagsContainerElement: HTMLDivElement;
	let viewOption = '';
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
				label: $i18n.t('Import JSON'),
				onClick: () => importInputElement?.click(),
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.skills_import
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

		loading = true;
		try {
			const res = await getSkillItems(localStorage.token, query, viewOption, page).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				filteredItems = res.items;
				total = res.total;
			}
		} catch (err) {
			console.error(err);
		} finally {
			loading = false;
		}
	};

	const handleSearchInput = () => {
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
	$: if (loaded && page && viewOption !== undefined) {
		loadSkillItems();
	}

	const cloneHandler = async (skill) => {
		const _skill = await getSkillById(localStorage.token, skill.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_skill) {
			sessionStorage.skill = JSON.stringify({
				..._skill,
				id: `${_skill.id}_clone`,
				name: `${_skill.name} (Clone)`
			});
			goto('/workspace/skills/create');
		}
	};

	const exportHandler = async (skill) => {
		const _skill = await getSkillById(localStorage.token, skill.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_skill) {
			let blob = new Blob([JSON.stringify([_skill])], {
				type: 'application/json'
			});
			saveAs(blob, `skill-${_skill.id}-export-${Date.now()}.json`);
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
		clearTimeout(searchDebounceTimer);
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Skills')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<input
		bind:this={importInputElement}
		bind:files={importFiles}
		type="file"
		accept=".md,.json"
		hidden
		on:change={() => {
			if (importFiles && importFiles.length > 0) {
				const file = importFiles[0];
				const ext = file.name.split('.').pop()?.toLowerCase();

				if (ext === 'json') {
					// JSON import: create skills via API
					const reader = new FileReader();
					reader.onload = async (event) => {
						try {
							const content = event.target?.result;
							if (typeof content !== 'string') return;

							const parsedSkills = JSON.parse(content);
							const items = Array.isArray(parsedSkills) ? parsedSkills : [parsedSkills];

							for (const skill of items) {
								await createNewSkill(localStorage.token, skill).catch((error) => {
									toast.error(`${error}`);
								});
							}

							toast.success($i18n.t('Skill imported successfully'));
							page = 1;
							loadSkillItems();
							_skills.set(await getSkills(localStorage.token));
						} catch (e) {
							toast.error($i18n.t('Invalid JSON file'));
						}
					};
					reader.readAsText(file);
				} else {
					// Markdown import: parse frontmatter and open in editor
					const reader = new FileReader();
					reader.onload = (event) => {
						const mdContent = event.target?.result;
						if (typeof mdContent === 'string') {
							const fm = parseFrontmatter(mdContent);
							const fileName = file.name.replace(/\.md$/, '');
							const rawName = fm.name || fileName;
							const displayName = formatSkillName(rawName);
							sessionStorage.skill = JSON.stringify({
								name: displayName,
								id: fm.name || '',
								description: fm.description || '',
								content: mdContent,
								is_active: true,
								access_grants: []
							});
							goto('/workspace/skills/create');
						}
					};
					reader.readAsText(file);
				}

				importInputElement.value = '';
			}
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
			<div class="my-1 gap-x-2 gap-y-0.5 grid lg:grid-cols-2">
				{#each filteredItems as skill}
					<Tooltip content={skill?.description ?? skill?.id}>
						<div
							class="flex space-x-4 text-left w-full px-2.5 py-1.5 transition rounded-2xl {skill.write_access
								? 'cursor-pointer hover:bg-gray-50/70 dark:hover:bg-gray-850/50'
								: 'cursor-not-allowed opacity-60'}"
						>
							{#if skill.write_access}
								<a
									class=" flex flex-1 space-x-3.5 cursor-pointer w-full"
									href={`/workspace/skills/edit?id=${encodeURIComponent(skill.id)}`}
								>
									<div class="flex items-center text-left">
										<div class=" flex-1 self-center">
											<Tooltip content={skill.id} placement="top-start">
												<div class="flex items-center gap-2">
													<div class="line-clamp-1 text-sm">
														{skill.name}
													</div>
													{#if !skill.is_active}
														<Badge type="muted" content={$i18n.t('Inactive')} />
													{/if}
												</div>
											</Tooltip>
											<div class="px-0.5">
												<div class="text-xs text-gray-500 shrink-0">
													<Tooltip
														content={skill?.user?.email ?? $i18n.t('Deleted User')}
														className="flex shrink-0"
														placement="top-start"
													>
														{$i18n.t('By {{name}}', {
															name: capitalizeFirstLetter(
																skill?.user?.name ?? skill?.user?.email ?? $i18n.t('Deleted User')
															)
														})}
													</Tooltip>
												</div>
											</div>
										</div>
									</div>
								</a>
							{:else}
								<div class=" flex flex-1 space-x-3.5 w-full">
									<div class="flex items-center text-left w-full">
										<div class="flex-1 self-center w-full">
											<div class="flex items-center justify-between w-full gap-2">
												<Tooltip content={skill.id} placement="top-start">
													<div class="flex items-center gap-2">
														<div class="line-clamp-1 text-sm">
															{skill.name}
														</div>
														{#if !skill.is_active}
															<Badge type="muted" content={$i18n.t('Inactive')} />
														{/if}
													</div>
												</Tooltip>
												<Badge type="muted" content={$i18n.t('Read Only')} />
											</div>
											<div class="px-0.5">
												<div class="text-xs text-gray-500 shrink-0">
													<Tooltip
														content={skill?.user?.email ?? $i18n.t('Deleted User')}
														className="flex shrink-0"
														placement="top-start"
													>
														{$i18n.t('By {{name}}', {
															name: capitalizeFirstLetter(
																skill?.user?.name ?? skill?.user?.email ?? $i18n.t('Deleted User')
															)
														})}
													</Tooltip>
												</div>
											</div>
										</div>
									</div>
								</div>
							{/if}
							{#if skill.write_access}
								<div class="flex flex-row gap-0.5 self-center">
									{#if shiftKey}
										<Tooltip content={$i18n.t('Delete')}>
											<button
												class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
												type="button"
												aria-label={$i18n.t('Delete')}
												on:click={() => {
													deleteHandler(skill);
												}}
											>
												<GarbageBin />
											</button>
										</Tooltip>
									{:else}
										<SkillMenu
											editHandler={() => {
												goto(`/workspace/skills/edit?id=${encodeURIComponent(skill.id)}`);
											}}
											cloneHandler={() => {
												cloneHandler(skill);
											}}
											exportHandler={() => {
												exportHandler(skill);
											}}
											deleteHandler={async () => {
												selectedSkill = skill;
												showDeleteConfirm = true;
											}}
											onClose={() => {}}
										>
											<button
												class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
												type="button"
											>
												<EllipsisHorizontal className="size-5" />
											</button>
										</SkillMenu>
									{/if}

									<button on:click|stopPropagation|preventDefault>
										<Tooltip content={skill.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
											<Switch
												bind:state={skill.is_active}
												on:change={async () => {
													toggleSkillById(localStorage.token, skill.id);
												}}
											/>
										</Tooltip>
									</button>
								</div>
							{/if}
						</div>
					</Tooltip>
				{/each}
			</div>

			{#if total > 30}
				<div class="flex justify-center mt-4 mb-2">
					<Pagination bind:page count={total} perPage={30} />
				</div>
			{/if}
		{:else}
			<div class=" w-full h-full flex flex-col justify-center items-center my-16 mb-24">
				<div class="max-w-md text-center">
					<div class=" text-3xl mb-3">📝</div>
					<div class=" text-lg font-normal mb-1">{$i18n.t('No skills found')}</div>
					<div class=" text-gray-500 text-center text-xs">
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
			{$i18n.t('This will delete')} <span class="  font-normal">{selectedSkill.name}</span>.
		</div>
	</DeleteConfirmDialog>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
