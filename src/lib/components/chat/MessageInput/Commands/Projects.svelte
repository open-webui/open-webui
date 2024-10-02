<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Fuse from 'fuse.js';

	import { createEventDispatcher, tick, getContext, onMount } from 'svelte';
	import { removeLastWordFromString, isValidHttpUrl } from '$lib/utils';
	import { projects } from '$lib/stores';

	const i18n = getContext('i18n');

	export let prompt = '';
	export let command = '';

	const dispatch = createEventDispatcher();
	let selectedIdx = 0;

	let fuse = null;

	let filteredProjects = [];
	$: if (fuse) {
		filteredProjects = command.slice(1)
			? fuse.search(command).map((e) => {
					return e.item;
				})
			: $projects;
	}

	$: if (command) {
		selectedIdx = 0;
	}

	type ObjectWithName = {
		name: string;
	};

	const findByName = (obj: ObjectWithName, command: string) => {
		const name = obj.name.toLowerCase();
		return name.includes(command.toLowerCase().split(' ')?.at(0)?.substring(1) ?? '');
	};

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredProjects.length - 1);
	};

	const confirmSelect = async (item) => {
		dispatch('select', item);

		prompt = removeLastWordFromString(prompt, command);
		const chatInputElement = document.getElementById('chat-textarea');

		await tick();
		chatInputElement?.focus();
		await tick();
	};

	const confirmSelectWeb = async (url) => {
		dispatch('url', url);

		prompt = removeLastWordFromString(prompt, command);
		const chatInputElement = document.getElementById('chat-textarea');

		await tick();
		chatInputElement?.focus();
		await tick();
	};

	const confirmSelectYoutube = async (url) => {
		dispatch('youtube', url);

		prompt = removeLastWordFromString(prompt, command);
		const chatInputElement = document.getElementById('chat-textarea');

		await tick();
		chatInputElement?.focus();
		await tick();
	};

	onMount(() => {
		fuse = new Fuse($projects, {
			keys: ['name', 'description']
		});
	});
</script>

{#if filteredProjects.length > 0 || prompt.split(' ')?.at(0)?.substring(1).startsWith('http')}
	<div
		id="commands-container"
		class="pl-1 pr-12 mb-3 text-left w-full absolute bottom-0 left-0 right-0 z-10"
	>
		<div class="flex w-full dark:border dark:border-gray-850 rounded-lg">
			<div class=" bg-gray-50 dark:bg-gray-850 w-10 rounded-l-lg text-center">
				<div class=" text-lg font-semibold mt-2">#</div>
			</div>

			<div
				class="max-h-60 flex flex-col w-full rounded-r-xl bg-white dark:bg-gray-900 dark:text-gray-100"
			>
				<div class="m-1 overflow-y-auto p-1 rounded-r-xl space-y-0.5 scrollbar-hidden">
					{#each filteredProjects as project, idx}
						<button
							class=" px-3 py-1.5 rounded-xl w-full text-left {idx === selectedIdx
								? ' bg-gray-50 dark:bg-gray-850 dark:text-gray-100 selected-command-option-button'
								: ''}"
							type="button"
							on:click={() => {
								console.log(project);
								confirmSelect(project);
							}}
							on:mousemove={() => {
								selectedIdx = idx;
							}}
							on:focus={() => {}}
						>
							<div class=" font-medium text-black dark:text-gray-100 flex items-center gap-1">
								<div class="line-clamp-1">
									{project.name}
								</div>

								{#if project?.meta?.legacy}
									<div
										class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded uppercase text-xs px-1"
									>
										Legacy Document
									</div>
								{:else}
									<div
										class="bg-green-500/20 text-green-700 dark:text-green-200 rounded uppercase text-xs px-1"
									>
										Project
									</div>
								{/if}
							</div>

							<div class=" text-xs text-gray-600 dark:text-gray-100 line-clamp-1">
								{project.description}
							</div>
						</button>
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
