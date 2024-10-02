<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, projects } from '$lib/stores';

	import { getProjects, deleteProjectById } from '$lib/apis/projects';

	import { blobToFile, transformFileName } from '$lib/utils';

	import { goto } from '$app/navigation';
	import Tooltip from '../common/Tooltip.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Pencil from '../icons/Pencil.svelte';
	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import ProjectMenu from './Projects/ProjectMenu.svelte';

	let query = '';
	let selectedProject = null;
	let showDeleteConfirm = false;

	let filteredProjects;
	$: filteredProjects = $projects.filter((project) => query === '' || project.name.includes(query));

	const deleteHandler = async (project) => {
		const res = await deleteProjectById(localStorage.token, project.id).catch((e) => {
			toast.error(e);
		});

		if (res) {
			projects.set(await getProjects(localStorage.token));
			toast.success($i18n.t('Project deleted successfully.'));
		}
	};

	onMount(async () => {
		projects.set(await getProjects(localStorage.token));
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Projects')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	on:confirm={() => {
		deleteHandler(selectedProject);
	}}
/>

<div class="mb-3">
	<div class="flex justify-between items-center">
		<div class="flex md:self-center text-lg font-medium px-0.5">
			{$i18n.t('Projects')}
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-200 dark:bg-gray-700" />
			<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{$projects.length}</span>
		</div>
	</div>
</div>

<div class=" flex w-full space-x-2">
	<div class="flex flex-1">
		<div class=" self-center ml-1 mr-3">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					fill-rule="evenodd"
					d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
		<input
			class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent"
			bind:value={query}
			placeholder={$i18n.t('Search Projects')}
		/>
	</div>

	<div>
		<button
			class=" px-2 py-2 rounded-xl border border-gray-200 dark:border-gray-600 dark:border-0 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition font-medium text-sm flex items-center space-x-1"
			aria-label={$i18n.t('Create Project')}
			on:click={() => {
				goto('/workspace/projects/create');
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
				/>
			</svg>
		</button>
	</div>
</div>

<hr class=" border-gray-50 dark:border-gray-850 my-2.5" />

<div class="my-3 mb-5 grid md:grid-cols-2 gap-2">
	{#each filteredProjects as project}
		{JSON.stringify(project)}
		<button
			class=" flex space-x-4 cursor-pointer text-left w-full px-4 py-3 border border-gray-50 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-850 rounded-xl"
		>
			<div class=" w-full">
				<div class="flex items-center justify-between -mt-1">
					<div class=" font-semibold line-clamp-1 h-fit">{project.name}</div>

					<div class=" flex self-center">
						<ProjectMenu
							on:delete={() => {
								selectedProject = project;
								showDeleteConfirm = true;
							}}
						/>
					</div>
				</div>

				<div class=" self-center flex-1">
					<div class=" text-xs overflow-hidden text-ellipsis line-clamp-1">
						{project.description}
					</div>

					<div class="mt-5 flex justify-between">
						<div>
							{#if project?.meta?.legacy}
								<div
									class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded uppercase text-xs font-bold px-1"
								>
									{$i18n.t('Legacy Document')}
								</div>
							{:else}
								<div
									class="bg-green-500/20 text-green-700 dark:text-green-200 rounded uppercase text-xs font-bold px-1"
								>
									{$i18n.t('Project')}
								</div>
							{/if}
						</div>
						<div class=" text-xs text-gray-500">
							Updated {dayjs(project.updated_at * 1000).fromNow()}
						</div>
					</div>
				</div>
			</div>
		</button>
	{/each}
</div>

<div class=" text-gray-500 text-xs mt-1 mb-2">
	ⓘ {$i18n.t("Use '#' in the prompt input to load and select your projects.")}
</div>
