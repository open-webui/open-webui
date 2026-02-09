<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick } from 'svelte';
	import { WEBUI_NAME, skills as _skills, user } from '$lib/stores';

	import {
		createNewSkill,
		deleteSkillById,
		exportSkills,
		getSkillList,
		getSkills,
		syncExternalSkills,
		toggleSkillById
	} from '$lib/apis/skills';
	import { capitalizeFirstLetter } from '$lib/utils';

	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import XMark from '../icons/XMark.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Switch from '../common/Switch.svelte';
	import ViewSelector from './common/ViewSelector.svelte';

	const i18n = getContext('i18n');

	type SkillListUser = {
		name?: string;
		email?: string;
	};

	type SkillListItem = {
		id: string;
		user_id: string;
		name: string;
		content: string;
		meta?: Record<string, unknown>;
		activation?: Record<string, unknown>;
		effects?: Record<string, unknown>;
		is_active?: boolean;
		priority?: number;
		access_control?: Record<string, unknown> | null;
		write_access?: boolean;
		user?: SkillListUser | null;
	};

	let loaded = false;
	let skillsImportInputElement: HTMLInputElement;
	let importFiles: FileList | null = null;

	let query = '';
	let viewOption = '';
	let skills: SkillListItem[] = [];
	let filteredItems: SkillListItem[] = [];
	let syncingExternalSkills = false;

	let tagsContainerElement: HTMLDivElement;

	$: if (skills && query !== undefined && viewOption !== undefined) {
		setFilteredItems();
	}

	const setFilteredItems = () => {
		filteredItems = skills.filter((s: SkillListItem) => {
			if (query === '' && viewOption === '') return true;
			const lowerQuery = query.toLowerCase();
			return (
				((s.name || '').toLowerCase().includes(lowerQuery) ||
					(s.id || '').toLowerCase().includes(lowerQuery) ||
					(s.user?.name || '').toLowerCase().includes(lowerQuery) ||
					(s.user?.email || '').toLowerCase().includes(lowerQuery)) &&
				(viewOption === '' ||
					(viewOption === 'created' && s.user_id === $user?.id) ||
					(viewOption === 'shared' && s.user_id !== $user?.id))
			);
		});
	};

	const init = async () => {
		skills = ((await getSkillList(localStorage.token)) ?? []) as SkillListItem[];
		_skills.set(((await getSkills(localStorage.token)) ?? []) as SkillListItem[]);
	};

	const deleteHandler = async (skill: SkillListItem) => {
		const res = await deleteSkillById(localStorage.token, skill.id).catch((error: unknown) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Skill deleted successfully'));
			await init();
		}
	};

	const toggleHandler = async (skill: SkillListItem) => {
		const res = await toggleSkillById(localStorage.token, skill.id).catch((error: unknown) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			await init();
		}
	};

	const syncExternalHandler = async () => {
		syncingExternalSkills = true;

		const res = await syncExternalSkills(localStorage.token).catch((error: unknown) => {
			toast.error(`${error}`);
			return null;
		});

		syncingExternalSkills = false;

		if (!res) {
			return;
		}

		const discovered = Number(res?.discovered ?? 0);
		const created = Number(res?.created ?? 0);
		const updated = Number(res?.updated ?? 0);
		const errors = Array.isArray(res?.errors) ? res.errors.length : 0;

		if (!res?.enabled) {
			toast.warning($i18n.t('External skills sync is disabled.'));
		} else {
			toast.success(
				$i18n.t('External sync done: {{discovered}} found, {{created}} created, {{updated}} updated', {
					discovered,
					created,
					updated
				})
			);

			if (errors > 0) {
				toast.warning($i18n.t('External sync had {{count}} errors', { count: errors }));
			}
		}

		await init();
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
		await init();
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Skills')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3">
		<input
			id="skills-import-input"
			bind:this={skillsImportInputElement}
			bind:files={importFiles}
			type="file"
			accept=".json"
			hidden
			on:change={() => {
				const reader = new FileReader();
				reader.onload = async (event) => {
					const target = event.target as FileReader | null;
					if (!target || typeof target.result !== 'string') {
						return;
					}

					const savedSkills = JSON.parse(target.result) as SkillListItem[];

					for (const skill of savedSkills) {
						await createNewSkill(localStorage.token, {
							id: skill.id,
							name: skill.name,
							content: skill.content,
							meta: skill.meta ?? {},
							activation: skill.activation ?? { mode: 'manual' },
							effects: skill.effects ?? {},
							is_active: skill.is_active ?? true,
							priority: skill.priority ?? 0,
							access_control: skill.access_control ?? {}
						}).catch((error: unknown) => {
							toast.error(`${error}`);
							return null;
						});
					}

					importFiles = null;
					skillsImportInputElement.value = '';
					await init();
				};

				if (importFiles?.[0]) {
					reader.readAsText(importFiles[0]);
				}
			}}
		/>

		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
				<div>{$i18n.t('Skills')}</div>
				<div class="text-lg font-medium text-gray-500 dark:text-gray-500">{filteredItems.length}</div>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				{#if $user?.role === 'admin' || $user?.permissions?.workspace?.skills_import}
					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition disabled:opacity-60 disabled:cursor-not-allowed"
						disabled={syncingExternalSkills}
						on:click={async () => {
							await syncExternalHandler();
						}}
					>
						{#if syncingExternalSkills}
							<div class="self-center mr-1"><Spinner className="size-3" /></div>
						{/if}
						<div class=" self-center font-medium line-clamp-1">
							{$i18n.t('Refresh External')}
						</div>
					</button>

					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
						on:click={() => {
							skillsImportInputElement.click();
						}}
					>
						<div class=" self-center font-medium line-clamp-1">{$i18n.t('Import')}</div>
					</button>
				{/if}

				{#if skills.length && ($user?.role === 'admin' || $user?.permissions?.workspace?.skills_export)}
					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
						on:click={async () => {
							const exported = (await exportSkills(localStorage.token).catch((error: unknown) => {
								toast.error(`${error}`);
								return null;
							})) as SkillListItem[] | null;

							if (exported) {
								let blob = new Blob([JSON.stringify(exported)], {
									type: 'application/json'
								});
								saveAs(blob, `skills-export-${Date.now()}.json`);
							}
						}}
					>
						<div class=" self-center font-medium line-clamp-1">{$i18n.t('Export')}</div>
					</button>
				{/if}

				<a
					class=" px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
					href="/workspace/skills/create"
				>
					<Plus className="size-3" strokeWidth="2.5" />
					<div class=" hidden md:block md:ml-1 text-xs">{$i18n.t('New Skill')}</div>
				</a>
			</div>
		</div>
	</div>

	<div class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30">
		<div class=" flex w-full space-x-2 py-0.5 px-3.5 pb-2">
			<div class="flex flex-1">
				<div class=" self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Skills')}
				/>

				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							on:click={() => {
								query = '';
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>
		</div>

		<div
			class="px-3 flex w-full bg-transparent overflow-x-auto scrollbar-none -mx-1"
			on:wheel={(e: WheelEvent) => {
				if (e.deltaY !== 0) {
					e.preventDefault();
					const target = e.currentTarget as HTMLElement | null;
					if (target) {
						target.scrollLeft += e.deltaY;
					}
				}
			}}
		>
			<div
				class="flex gap-0.5 w-fit text-center text-sm rounded-full bg-transparent px-1.5 whitespace-nowrap"
				bind:this={tagsContainerElement}
			>
				<ViewSelector
					bind:value={viewOption}
					onChange={async (value) => {
						localStorage.workspaceViewOption = value;
						await tick();
					}}
				/>
			</div>
		</div>

		{#if (filteredItems ?? []).length !== 0}
			<div class="my-2 gap-2 grid px-3 lg:grid-cols-2">
				{#each filteredItems as skill}
					<div class="flex space-x-4 text-left w-full px-3 py-2.5 transition rounded-2xl dark:hover:bg-gray-850/50 hover:bg-gray-50">
						<div class="flex flex-col flex-1 min-w-0">
							{#if skill.write_access}
								<a href={`/workspace/skills/edit?id=${encodeURIComponent(skill.id)}`}>
									<div class="font-medium line-clamp-1 capitalize">{skill.name}</div>
								</a>
							{:else}
								<div class="font-medium line-clamp-1 capitalize">{skill.name}</div>
							{/if}

							<div class="text-xs overflow-hidden text-ellipsis line-clamp-1 text-gray-500">
								{skill.id}
							</div>

							<div class="text-xs mt-1 text-gray-500 flex items-center gap-1.5">
								<Tooltip
									content={skill?.user?.email ?? $i18n.t('Deleted User')}
									className="flex shrink-0"
									placement="top-start"
								>
									<div class="shrink-0">
										{$i18n.t('By {{name}}', {
											name: capitalizeFirstLetter(
												skill?.user?.name ?? skill?.user?.email ?? $i18n.t('Deleted User')
											)
										})}
									</div>
								</Tooltip>

								<span>·</span>
								<span>{$i18n.t('Priority')}: {skill.priority ?? 0}</span>
							</div>
						</div>

						<div class="flex flex-row gap-1 self-center">
							{#if !skill.write_access}
								<Badge type="muted" content={$i18n.t('Read Only')} />
							{/if}

							{#if skill.write_access}
								<button
									class="self-center"
									type="button"
									on:click={() => {
										toggleHandler(skill);
									}}
								>
									<Tooltip content={skill.is_active ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
										<Switch state={Boolean(skill.is_active)} />
									</Tooltip>
								</button>

								<button
									class="text-xs px-2 py-1.5 rounded-xl bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 transition"
									type="button"
									on:click={() => {
										deleteHandler(skill);
									}}
								>
									{$i18n.t('Delete')}
								</button>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class=" w-full h-full flex flex-col justify-center items-center my-16 mb-24">
				<div class="max-w-md text-center">
					<div class=" text-3xl mb-3">😕</div>
					<div class=" text-lg font-medium mb-1">{$i18n.t('No skills found')}</div>
					<div class=" text-gray-500 text-center text-xs">
						{$i18n.t('Try adjusting your search or filter to find what you are looking for.')}
					</div>
				</div>
			</div>
		{/if}
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
